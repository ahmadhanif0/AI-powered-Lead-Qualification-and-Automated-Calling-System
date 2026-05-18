from app.repositories.lead_repository import LeadRepository
from app.queues.tasks import start_lead_call_task
from app.websocket.manager import manager
from datetime import datetime, timedelta, timezone
from app.queues.tasks import retry_call_task
from app.services.crm_update_service import CRMUpdateService
from app.services.notification_service import NotificationService
from app.repositories.retry_queue_repository import RetryQueueRepository
from app.logs.logger import logger

# Fallback delays (seconds) when no RetryConfig exists for a user
DEFAULT_DELAYS = {
    "call_later":  3600,   # 60 minutes
    "no_response": 1800,   # 30 minutes
}


async def _get_retry_delay(user_id, outcome_type: str) -> int:
    """Return retry delay in seconds from user config, or fallback default."""
    if not user_id:
        return DEFAULT_DELAYS.get(outcome_type, 1800)
    try:
        from app.models.retry_config import RetryConfig
        config = await RetryConfig.get_or_none(user_id=user_id, outcome_type=outcome_type)
        if config and config.is_active:
            return config.retry_delay_minutes * 60
    except Exception as e:
        logger.warning(f"Could not fetch retry config for user {user_id}: {e}")
    return DEFAULT_DELAYS.get(outcome_type, 1800)


class WorkflowActions:

    def __init__(self):
        self.repo         = LeadRepository()
        self.crm_service  = CRMUpdateService()
        self.retry_repo   = RetryQueueRepository()
        self.notifier     = NotificationService()

    # =====================================================
    # 1. INTERESTED → "Booked"
    # =====================================================

    async def handle_interested(self, lead: dict):
        await self.repo.update_lead_status(lead_id=lead["id"], status="Booked")
        await self.repo.update_call_status(lead_id=lead["id"], status="completed")

        await self.crm_service.update_stage(lead_id=lead["id"], new_stage="marketingqualifiedlead")
        await self.crm_service.update_lead_status_in_crm(lead_id=lead["id"], status="Booked")

        await manager.broadcast({"event": "ai_decision", "lead_id": lead["id"], "decision": "Interested", "status": "Booked"})

        await self.notifier.send_notification(lead=lead, decision="Interested")

        logger.info(f"Lead {lead['id']} → Booked")
        return {"action": "crm_updated", "status": "Booked"}

    # =====================================================
    # 2. CALL LATER → "Pending"  (dynamic delay)
    # =====================================================

    async def handle_call_later(self, lead: dict):
        # Resolve user_id from lead
        lead_obj = await self.repo.get_by_id(lead["id"])
        user_id  = getattr(lead_obj, "user_id", None)

        delay_seconds = await _get_retry_delay(user_id, "call_later")
        retry_time    = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

        await self.repo.update_call_status(lead_id=lead["id"], status="call_later")

        new_retry_count = (lead_obj.retry_count or 0) + 1
        await self.repo.update_retry_info(
            lead_id=lead["id"],
            retry_count=new_retry_count,
            next_retry_at=retry_time,
            status="Pending",
        )

        await self.crm_service.update_lead_status_in_crm(lead_id=lead["id"], status="Pending")

        await self.retry_repo.create_retry({
            "lead_id":      lead["id"],
            "retry_reason": "call_later",
            "retry_at":     retry_time,
        })
        retry_call_task.apply_async(args=[lead["id"]], countdown=delay_seconds)

        logger.info(f"Lead {lead['id']} → Pending (call later, delay={delay_seconds}s, attempt #{new_retry_count})")

        await manager.broadcast({"event": "ai_decision", "lead_id": lead["id"], "decision": "Call Later", "status": "Pending"})
        await self.crm_service.update_stage(lead_id=lead["id"], new_stage="lead")

        return {"action": "retry_scheduled", "retry_at": str(retry_time)}

    # =====================================================
    # 3. NOT INTERESTED → "Won't Follow Up"
    # =====================================================

    async def handle_not_interested(self, lead: dict):
        await self.repo.update_lead_status(lead_id=lead["id"], status="Won't Follow Up")
        await self.repo.update_call_status(lead_id=lead["id"], status="completed")

        await self.crm_service.update_stage(lead_id=lead["id"], new_stage="subscriber")
        await self.crm_service.update_lead_status_in_crm(lead_id=lead["id"], status="Won't Follow Up")

        await manager.broadcast({"event": "ai_decision", "lead_id": lead["id"], "decision": "Not Interested", "status": "Won't Follow Up"})

        logger.info(f"Lead {lead['id']} → Won't Follow Up")
        return {"action": "crm_updated", "status": "Won't Follow Up"}

    # =====================================================
    # 4. WRONG NUMBER → "Rejected"
    # =====================================================

    async def handle_wrong_number(self, lead: dict):
        await self.repo.update_lead_status(lead_id=lead["id"], status="Rejected")
        await self.repo.update_call_status(lead_id=lead["id"], status="wrong_number")

        await self.crm_service.update_lead_status_in_crm(lead_id=lead["id"], status="Rejected")

        await manager.broadcast({"event": "ai_decision", "lead_id": lead["id"], "decision": "Wrong Number", "status": "Rejected"})

        logger.info(f"Lead {lead['id']} → Rejected (wrong number)")
        return {"action": "invalid_lead"}

    # =====================================================
    # 5. NO RESPONSE → "Rejected"  (dynamic delay)
    # =====================================================

    async def handle_no_response(self, lead: dict):
        lead_obj = await self.repo.get_by_id(lead["id"])
        user_id  = getattr(lead_obj, "user_id", None)

        delay_seconds = await _get_retry_delay(user_id, "no_response")
        retry_time    = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

        await self.repo.update_call_status(lead_id=lead["id"], status="call_not_attended")

        new_retry_count = (lead_obj.retry_count or 0) + 1
        await self.repo.update_retry_info(
            lead_id=lead["id"],
            retry_count=new_retry_count,
            next_retry_at=retry_time,
            status="Rejected",
        )

        await self.crm_service.update_lead_status_in_crm(lead_id=lead["id"], status="Rejected")

        await self.retry_repo.create_retry({
            "lead_id":      lead["id"],
            "retry_reason": "no_response",
            "retry_at":     retry_time,
        })
        retry_call_task.apply_async(args=[lead["id"]], countdown=delay_seconds)

        logger.info(f"Lead {lead['id']} → Rejected (no response, delay={delay_seconds}s, attempt #{new_retry_count})")

        await manager.broadcast({"event": "ai_decision", "lead_id": lead["id"], "decision": "No Response", "status": "Rejected"})

        return {"action": "retry_scheduled", "retry_at": str(retry_time)}

    # =====================================================
    # AUTO CALL
    # =====================================================

    async def trigger_auto_call(self, lead: dict):
        logger.info(f"Auto-triggering call for lead {lead['id']}")
        start_lead_call_task.delay(lead["id"])
        return {"action": "call_queued", "lead_id": lead["id"]}

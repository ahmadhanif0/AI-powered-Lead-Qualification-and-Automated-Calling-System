from app.repositories.lead_repository import LeadRepository
from app.queues.tasks import start_lead_call_task
from app.websocket.manager import manager
from datetime import datetime, timedelta, timezone
from app.queues.tasks import retry_call_task
from app.services.crm_update_service import CRMUpdateService
from app.services.notification_service import NotificationService
from app.repositories.retry_queue_repository import RetryQueueRepository
from app.logs.logger import logger


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

        # Local DB update
        await self.repo.update_lead_status(
            lead_id=lead["id"],
            status="Booked"
        )
        await self.repo.update_call_status(
            lead_id=lead["id"],
            status="completed"
        )

        # HubSpot lifecycle stage
        await self.crm_service.update_stage(
            lead_id=lead["id"],
            new_stage="marketingqualifiedlead"
        )

        # Sync new status value to CRM
        await self.crm_service.update_lead_status_in_crm(
            lead_id=lead["id"],
            status="Booked"
        )

        # Real-time dashboard event
        await manager.broadcast({
            "event":    "ai_decision",
            "lead_id":  lead["id"],
            "decision": "Interested",
            "status":   "Booked"
        })

        # Sales/admin notification
        await self.notifier.send_notification(
            lead=lead,
            decision="Interested"
        )

        logger.info(f"Lead {lead['id']} → Booked")

        return {"action": "crm_updated", "status": "Booked"}

    # =====================================================
    # 2. CALL LATER → "Pending"
    # =====================================================

    async def handle_call_later(self, lead: dict):

        retry_time = datetime.now(timezone.utc) + timedelta(hours=1)

        await self.repo.update_call_status(
            lead_id=lead["id"],
            status="call_later"
        )

        # Increment retry counter
        lead_obj        = await self.repo.get_by_id(lead["id"])
        new_retry_count = (lead_obj.retry_count or 0) + 1

        await self.repo.update_retry_info(
            lead_id=lead["id"],
            retry_count=new_retry_count,
            next_retry_at=retry_time,
            status="Pending"
        )

        # Sync to CRM
        await self.crm_service.update_lead_status_in_crm(
            lead_id=lead["id"],
            status="Pending"
        )

        # Retry queue entry + Celery task
        await self.retry_repo.create_retry({
            "lead_id":      lead["id"],
            "retry_reason": "call_later",
            "retry_at":     retry_time
        })
        retry_call_task.apply_async(
            args=[lead["id"]],
            countdown=36000   # 60 minutes
        )

        logger.info(
            f"Lead {lead['id']} → Pending (call later, attempt #{new_retry_count})"
        )

        await manager.broadcast({
            "event":    "ai_decision",
            "lead_id":  lead["id"],
            "decision": "Call Later",
            "status":   "Pending"
        })

        await self.crm_service.update_stage(
            lead_id=lead["id"],
            new_stage="lead"
        )

        return {"action": "retry_scheduled", "retry_at": str(retry_time)}

    # =====================================================
    # 3. NOT INTERESTED → "Won't Follow Up"
    # =====================================================

    async def handle_not_interested(self, lead: dict):

        await self.repo.update_lead_status(
            lead_id=lead["id"],
            status="Won't Follow Up"
        )
        await self.repo.update_call_status(
            lead_id=lead["id"],
            status="completed"
        )

        await self.crm_service.update_stage(
            lead_id=lead["id"],
            new_stage="subscriber"
        )
        await self.crm_service.update_lead_status_in_crm(
            lead_id=lead["id"],
            status="Won't Follow Up"
        )

        await manager.broadcast({
            "event":    "ai_decision",
            "lead_id":  lead["id"],
            "decision": "Not Interested",
            "status":   "Won't Follow Up"
        })

        logger.info(f"Lead {lead['id']} → Won't Follow Up (not interested)")

        return {"action": "crm_updated", "status": "Won't Follow Up"}

    # =====================================================
    # 4. WRONG NUMBER → "Rejected"
    # =====================================================

    async def handle_wrong_number(self, lead: dict):

        await self.repo.update_lead_status(
            lead_id=lead["id"],
            status="Rejected"
        )
        await self.repo.update_call_status(
            lead_id=lead["id"],
            status="wrong_number"
        )

        await self.crm_service.update_lead_status_in_crm(
            lead_id=lead["id"],
            status="Rejected"
        )

        await manager.broadcast({
            "event":    "ai_decision",
            "lead_id":  lead["id"],
            "decision": "Wrong Number",
            "status":   "Rejected"
        })

        logger.info(f"Lead {lead['id']} → Rejected (wrong number)")

        return {"action": "invalid_lead"}

    # =====================================================
    # 5. NO RESPONSE → "Rejected"
    # =====================================================

    async def handle_no_response(self, lead: dict):

        retry_time = datetime.now(timezone.utc) + timedelta(minutes=30)

        await self.repo.update_call_status(
            lead_id=lead["id"],
            status="call_not_attended"
        )

        # Increment retry counter
        lead_obj        = await self.repo.get_by_id(lead["id"])
        new_retry_count = (lead_obj.retry_count or 0) + 1

        await self.repo.update_retry_info(
            lead_id=lead["id"],
            retry_count=new_retry_count,
            next_retry_at=retry_time,
            status="Rejected"
        )

        # Sync to CRM
        await self.crm_service.update_lead_status_in_crm(
            lead_id=lead["id"],
            status="Rejected"
        )

        # Retry queue entry + Celery task
        await self.retry_repo.create_retry({
            "lead_id":      lead["id"],
            "retry_reason": "no_response",
            "retry_at":     retry_time
        })
        retry_call_task.apply_async(
            args=[lead["id"]],
            countdown=1800   # 30 minutes — matches retry_at
        )

        logger.info(
            f"Lead {lead['id']} → Rejected "
            f"(no response, attempt #{new_retry_count})"
        )

        await manager.broadcast({
            "event":    "ai_decision",
            "lead_id":  lead["id"],
            "decision": "No Response",
            "status":   "Rejected"
        })

        return {"action": "retry_scheduled", "retry_at": str(retry_time)}

    # =====================================================
    # AUTO CALL
    # =====================================================

    async def trigger_auto_call(self, lead: dict):

        logger.info(f"Auto-triggering call for lead {lead['id']}")

        start_lead_call_task.delay(lead["id"])

        return {"action": "call_queued", "lead_id": lead["id"]}

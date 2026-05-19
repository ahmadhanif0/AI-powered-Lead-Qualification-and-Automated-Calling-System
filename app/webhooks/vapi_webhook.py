from fastapi import APIRouter, Request

from app.ai.decision_engine import DecisionEngine
from app.workflows.workflow_engine import WorkflowEngine
from app.repositories.lead_repository import LeadRepository
from app.repositories.call_log_repository import CallLogRepository
from app.services.ai_conversation_scoring_service import (
    AIConversationScoringService
)
from app.logs.logger import logger

router = APIRouter()


@router.post("/vapi/webhook")
async def vapi_webhook(request: Request):

    data = await request.json()

    logger.info(f"FULL VAPI WEBHOOK: {data}")

    message = data.get("message", {})

    message_type = message.get("type")

    logger.info(f"VAPI MESSAGE TYPE: {message_type}")

    # =====================================================
    # STATUS UPDATE EVENTS
    # =====================================================

    if message_type == "status-update":

        call_data = message.get("call", {})

        metadata = call_data.get("metadata", {})

        lead_id = metadata.get("lead_id")

        ended_reason = message.get("endedReason")

        vapi_call_id = call_data.get("id")

        logger.info(f"STATUS UPDATE ENDED REASON: {ended_reason}")

        if not lead_id:
            return {"status": "ignored"}

        repo = LeadRepository()

        call_log_repo = CallLogRepository()

        # -----------------------------------------
        # CUSTOMER DID NOT ANSWER
        # -----------------------------------------

        if ended_reason == "customer-did-not-answer":

            await repo.update_call_status(
                lead_id=int(lead_id),
                status="call_not_attended"
            )

            await call_log_repo.update_log(
                vapi_call_id=vapi_call_id,
                data={
                    "call_status": "call_not_attended"
                }
            )

            # ── Deduplication guard ──────────────────────────────────
            # VAPI fires BOTH status-update (customer-did-not-answer) AND
            # end-of-call-report for the same missed call.  If the
            # end-of-call-report was already processed first (ai_decision
            # is set on the CallLog), the workflow has already run —
            # skip it here to prevent double retry entries and double
            # retry_count increments.
            existing_log = await call_log_repo.get_log_by_vapi_id(vapi_call_id)
            if existing_log and existing_log.ai_decision:
                logger.info(
                    f"[Webhook] status-update skipping workflow for vapi_call_id={vapi_call_id} "
                    f"— end-of-call-report already processed (ai_decision={existing_log.ai_decision})"
                )
                return {"status": "call_not_attended_deduped"}

            workflow = WorkflowEngine()

            lead = await repo.get_by_id(int(lead_id))

            await workflow.handle_result(
                lead={
                    "id": lead.id,
                    "phone": lead.phone,
                    "email": lead.email,
                    "company": lead.company
                },
                result="No Response"
            )

            return {
                "status": "call_not_attended"
            }

        # -----------------------------------------
        # CUSTOMER REJECTED
        # -----------------------------------------

        if ended_reason == "customer-ended-call":

            await repo.update_call_status(
                lead_id=int(lead_id),
                status="call_rejected"
            )

            await call_log_repo.update_log(
                vapi_call_id=vapi_call_id,
                data={
                    "call_status": "call_rejected"
                }
            )

            return {
                "status": "call_rejected"
            }

        return {
            "status": "ignored_status_update"
        }

    # =====================================================
    # ONLY PROCESS FINAL REPORT
    # =====================================================

    if message_type != "end-of-call-report":

        return {
            "status": "ignored",
            "message_type": message_type
        }

    # =====================================================
    # FINAL REPORT
    # =====================================================

    call_data = message.get("call", {})

    vapi_call_id = call_data.get("id")

    # FIX (Issue 3): VAPI sends durationSeconds at the message level
    # in end-of-call-report, not inside the call object.
    # Try message level first, fall back to call object.
    duration = (
        message.get("durationSeconds")
        or call_data.get("durationSeconds")
        or 0
    )

    logger.info(f"Call duration extracted: {duration}s")

    metadata = call_data.get("metadata", {})

    lead_id = metadata.get("lead_id")

    logger.info(f"Metadata: {metadata}")

    if not lead_id:

        logger.error("lead_id missing in metadata")

        return {
            "status": "ignored",
            "reason": "missing lead_id"
        }

    artifact = message.get("artifact", {})

    transcript = artifact.get("transcript")

    if not transcript:

        messages = artifact.get("messages", [])

        transcript = "\n".join([
            f"{m.get('role')}: {m.get('message')}"
            for m in messages
            if m.get("message")
        ])

    logger.info(f"Transcript: {transcript}")

    engine = DecisionEngine()

    result = engine.analyze(transcript)

    logger.info(f"AI Decision: {result}")

    ai_scoring = AIConversationScoringService()

    ai_score = ai_scoring.calculate_score(
        transcript=transcript,
        decision=result
    )

    repo = LeadRepository()

    await repo.update_lead_score(
        lead_id=int(lead_id),
        ai_score=ai_score
    )

    await repo.save_transcript_and_decision(
        lead_id=int(lead_id),
        transcript=transcript,
        decision=result
    )

    await repo.update_call_status(
        lead_id=int(lead_id),
        status="completed"
    )

    call_log_repo = CallLogRepository()

    await call_log_repo.update_log(
        vapi_call_id=vapi_call_id,
        data={
            "transcript":       transcript,
            "ai_decision":      result,
            "call_status":      "completed",
            "duration_seconds": duration,
            "recording_url":    artifact.get("recordingUrl") or message.get("recordingUrl"),
        }
    )

    workflow = WorkflowEngine()

    lead = await repo.get_by_id(int(lead_id))

    try:
        await workflow.handle_result(
            lead={
                "id": lead.id,
                "phone": lead.phone,
                "email": lead.email,
                "company": lead.company
            },
            result=result
        )
    except Exception as wf_err:
        # Workflow failure (e.g. CRM sync error) must never swallow the
        # status update.  Log the error and apply the status mapping directly
        # so the lead always reflects the AI decision.
        logger.error(f"[Webhook] WorkflowEngine failed for lead {lead_id}: {wf_err}")
        _DECISION_TO_STATUS = {
            "interested":     "Booked",
            "not interested": "Won't Follow Up",
            "call later":     "Pending",
            "wrong number":   "Rejected",
            "no response":    "Rejected",
        }
        fallback_status = _DECISION_TO_STATUS.get(result.lower().strip(), "Pending")
        try:
            await repo.update_lead_status(lead_id=int(lead_id), status=fallback_status)
            logger.info(f"[Webhook] Fallback status set: lead {lead_id} → {fallback_status}")
        except Exception as fb_err:
            logger.error(f"[Webhook] Fallback status update also failed for lead {lead_id}: {fb_err}")

    return {
        "status": "processed",
        "decision": result,
        "ai_score": ai_score
    }
from app.models.call_log import CallLog
from app.logs.logger import logger


class CallLogRepository:

    @staticmethod
    async def create_log(data: dict):

        return await CallLog.create(**data)

    @staticmethod
    async def get_log_by_vapi_id(vapi_call_id: str):
        """Fetch the CallLog for a given VAPI call ID, or None if not found."""
        return await CallLog.filter(vapi_call_id=vapi_call_id).first()

    @staticmethod
    async def update_log(vapi_call_id: str, data: dict):

        log = await CallLog.filter(
            vapi_call_id=vapi_call_id
        ).first()

        if not log:
            logger.warning(f"[CallLog] update_log: no record found for vapi_call_id={vapi_call_id}")
            return None

        for key, value in data.items():
            setattr(log, key, value)

        await log.save()

        logger.info(f"[CallLog] updated vapi_call_id={vapi_call_id}")

        return log
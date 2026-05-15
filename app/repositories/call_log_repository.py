from app.models.call_log import CallLog


class CallLogRepository:

    @staticmethod
    async def create_log(data: dict):

        return await CallLog.create(**data)

    @staticmethod
    async def update_log(vapi_call_id: str, data: dict):

        log = await CallLog.filter(
            vapi_call_id=vapi_call_id
        ).first()

        if not log:
            # ADD THIS DEBUG
            print(f"[CALL LOG NOT FOUND] vapi_call_id={vapi_call_id}")
            return None

        for key, value in data.items():
            setattr(log, key, value)

        await log.save()

        print(f"[CALL LOG UPDATED] {vapi_call_id}")

        return log
from app.models.user_activity import UserActivity
from app.logs.logger import logger


async def log_activity(
    user_id: int,
    action: str,
    details: dict = None,
    ip: str = None,
):
    """
    Persist a user activity record.
    Never raises — a logging failure must not break the caller.

    Actions used in this system:
        login, logout, signup,
        create_assistant, delete_assistant,
        start_call,
        sync_crm, sync_crm_async,
        admin_updated_user, admin_deleted_user,
        admin_suspended_user, admin_activated_user,
        admin_reset_password
    """
    try:
        await UserActivity.create(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip,
        )
    except Exception as e:
        logger.error(f"Failed to log activity [{action}] for user {user_id}: {e}")

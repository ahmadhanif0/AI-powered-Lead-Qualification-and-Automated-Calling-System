from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.retry_config import RetryConfig

router = APIRouter(prefix="/retry-configs", tags=["Retry Config"])

VALID_OUTCOMES = {"call_later", "no_response"}


class UpdateRetryConfigRequest(BaseModel):
    retry_delay_minutes: int
    max_retry_attempts:  int

    @field_validator("retry_delay_minutes")
    @classmethod
    def validate_delay(cls, v):
        if not (5 <= v <= 1440):
            raise ValueError("retry_delay_minutes must be between 5 and 1440 (5 min – 24 hours)")
        return v

    @field_validator("max_retry_attempts")
    @classmethod
    def validate_attempts(cls, v):
        if v not in (1, 2, 3, 5):
            raise ValueError("max_retry_attempts must be 1, 2, 3, or 5")
        return v


def _config_dict(c: RetryConfig) -> dict:
    return {
        "id":                   c.id,
        "outcome_type":         c.outcome_type,
        "retry_delay_minutes":  c.retry_delay_minutes,
        "max_retry_attempts":   c.max_retry_attempts,
        "is_active":            c.is_active,
    }


@router.get("/")
async def list_retry_configs(current_user: User = Depends(get_current_user)):
    configs = await RetryConfig.filter(user_id=current_user.id).all()
    return [_config_dict(c) for c in configs]


@router.put("/{outcome_type}")
async def update_retry_config(
    outcome_type: str,
    body: UpdateRetryConfigRequest,
    current_user: User = Depends(get_current_user),
):
    if outcome_type not in VALID_OUTCOMES:
        raise HTTPException(status_code=400, detail=f"outcome_type must be one of {VALID_OUTCOMES}")

    config = await RetryConfig.get_or_none(user_id=current_user.id, outcome_type=outcome_type)
    if not config:
        # Auto-create if missing (e.g. legacy user)
        config = await RetryConfig.create(
            user_id=current_user.id,
            outcome_type=outcome_type,
            retry_delay_minutes=body.retry_delay_minutes,
            max_retry_attempts=body.max_retry_attempts,
        )
    else:
        config.retry_delay_minutes = body.retry_delay_minutes
        config.max_retry_attempts  = body.max_retry_attempts
        await config.save()

    return _config_dict(config)

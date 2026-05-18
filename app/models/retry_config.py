from tortoise import fields
from tortoise.models import Model


class RetryConfig(Model):
    id                  = fields.IntField(pk=True)
    user                = fields.ForeignKeyField("models.User", related_name="retry_configs", on_delete=fields.CASCADE)
    outcome_type        = fields.CharField(max_length=50)   # 'call_later' | 'no_response'
    retry_delay_minutes = fields.IntField(default=30)
    max_retry_attempts  = fields.IntField(default=3)
    is_active           = fields.BooleanField(default=True)
    created_at          = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table          = "retry_configs"
        unique_together = (("user", "outcome_type"),)

from tortoise import fields
from tortoise.models import Model


class RetryQueue(Model):

    id = fields.IntField(pk=True)

    lead = fields.ForeignKeyField(
        "models.Lead",
        related_name="retries",
        on_delete=fields.CASCADE
    )

    retry_reason = fields.CharField(max_length=100)

    retry_status = fields.CharField(max_length=100, default="pending")

    retry_at = fields.DatetimeField()

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "retry_queue"
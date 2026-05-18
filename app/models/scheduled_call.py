from tortoise import fields
from tortoise.models import Model


class ScheduledCall(Model):
    id           = fields.IntField(pk=True)
    user         = fields.ForeignKeyField("models.User",      related_name="scheduled_calls", on_delete=fields.CASCADE)
    lead         = fields.ForeignKeyField("models.Lead",      related_name="scheduled_calls", on_delete=fields.CASCADE)
    assistant    = fields.ForeignKeyField("models.Assistant", related_name="scheduled_calls", on_delete=fields.CASCADE)
    scheduled_at = fields.DatetimeField()
    celery_task_id = fields.CharField(max_length=255, null=True)
    status       = fields.CharField(max_length=20, default="pending")  # pending | completed | cancelled
    created_at   = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "scheduled_calls"

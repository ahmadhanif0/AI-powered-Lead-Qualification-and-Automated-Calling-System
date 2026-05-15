from tortoise import fields
from tortoise.models import Model


class CallLog(Model):

    id = fields.IntField(pk=True)

    # lead = fields.ForeignKeyField(
    #     "models.Lead",
    #     related_name="call_logs",
    #     on_delete=fields.CASCADE
    # )

    lead_id = fields.IntField()

    vapi_call_id = fields.CharField(
        max_length=255,
        null=True
    )

    twilio_number = fields.CharField(
        max_length=100,
        null=True
    )

    assistant_name = fields.CharField(
        max_length=255,
        null=True
    )

    transcript = fields.TextField(null=True)

    ai_decision = fields.CharField(
        max_length=100,
        null=True
    )

    call_status = fields.CharField(
        max_length=100,
        default="queued"
    )

    duration_seconds = fields.IntField(
        null=True
    )

    created_at = fields.DatetimeField(
        auto_now_add=True
    )

    class Meta:
        table = "call_logs"
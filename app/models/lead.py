from tortoise import fields
from tortoise.models import Model


class Lead(Model):
    id = fields.IntField(pk=True)

    # Multi-tenancy — which user owns this lead
    user = fields.ForeignKeyField(
        "models.User",
        related_name="leads",
        null=True,          # null=True so existing rows don't break before migration
        on_delete=fields.CASCADE
    )

    hubspot_id = fields.CharField(max_length=255, unique=True)

    first_name = fields.CharField(max_length=255, null=True)
    last_name  = fields.CharField(max_length=255, null=True)
    email      = fields.CharField(max_length=255, null=True)
    phone      = fields.CharField(max_length=100, null=True)
    company    = fields.CharField(max_length=255, null=True)
    lead_stage = fields.CharField(max_length=255, null=True)

    score = fields.FloatField(default=0)

    status      = fields.CharField(max_length=100, default="Pending")
    call_status = fields.CharField(max_length=50,  default="pending")

    call_sid      = fields.CharField(max_length=255, null=True)
    call_provider = fields.CharField(max_length=100, null=True)

    last_call_at = fields.DatetimeField(null=True)
    retry_count  = fields.IntField(default=0)

    last_transcript = fields.TextField(null=True)
    ai_decision     = fields.CharField(max_length=100, null=True)
    next_retry_at   = fields.DatetimeField(null=True)

    assistant = fields.ForeignKeyField(
        "models.Assistant",
        related_name="leads",
        null=True,
        on_delete=fields.SET_NULL
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "leads"

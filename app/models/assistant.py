from tortoise import fields
from tortoise.models import Model


class Assistant(Model):
    id = fields.IntField(pk=True)

    # Multi-tenancy — which user owns this assistant
    user = fields.ForeignKeyField(
        "models.User",
        related_name="assistants",
        null=True,
        on_delete=fields.CASCADE
    )

    name           = fields.CharField(max_length=255)
    system_prompt  = fields.TextField()
    first_message  = fields.TextField()
    voice_id       = fields.CharField(max_length=100, default="Elliot")
    model_provider = fields.CharField(max_length=50,  default="openai")
    model_name     = fields.CharField(max_length=50,  default="gpt-4.1")

    vapi_assistant_id = fields.CharField(max_length=255, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "assistants"

from tortoise import fields
from tortoise.models import Model


class UserCRM(Model):
    id       = fields.IntField(pk=True)
    user     = fields.ForeignKeyField("models.User", related_name="crm_configs", on_delete=fields.CASCADE)
    crm_type = fields.CharField(max_length=50, default="hubspot")

    # OAuth tokens (store as plain text; encrypt at rest in production)
    access_token      = fields.TextField(null=True)
    refresh_token     = fields.TextField(null=True)
    token_expires_at  = fields.DatetimeField(null=True)

    # HubSpot-specific
    hubspot_portal_id = fields.CharField(max_length=100, null=True)

    is_connected = fields.BooleanField(default=False)
    last_sync_at = fields.DatetimeField(null=True)
    created_at   = fields.DatetimeField(auto_now_add=True)
    updated_at   = fields.DatetimeField(auto_now=True)

    class Meta:
        table          = "user_crms"
        unique_together = (("user", "crm_type"),)

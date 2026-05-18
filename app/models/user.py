from tortoise import fields
from tortoise.models import Model


class User(Model):
    id            = fields.IntField(pk=True)
    email         = fields.CharField(max_length=255, unique=True)
    password_hash = fields.CharField(max_length=255)
    full_name     = fields.CharField(max_length=255)
    role          = fields.CharField(max_length=20, default="user")
    is_active     = fields.BooleanField(default=True)
    is_suspended  = fields.BooleanField(default=False)
    created_at    = fields.DatetimeField(auto_now_add=True)
    last_login    = fields.DatetimeField(null=True)

    # Notification preferences
    email_on_interested      = fields.BooleanField(default=True)
    email_on_call_completed  = fields.BooleanField(default=False)
    email_on_retry_failed    = fields.BooleanField(default=True)

    class Meta:
        table = "users"

from tortoise import fields
from tortoise.models import Model


class UserActivity(Model):
    id         = fields.IntField(pk=True)
    user       = fields.ForeignKeyField("models.User", related_name="activities", on_delete=fields.CASCADE)
    action     = fields.CharField(max_length=100)   # 'login', 'logout', 'create_assistant', etc.
    details    = fields.JSONField(null=True)
    ip_address = fields.CharField(max_length=50, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_activities"

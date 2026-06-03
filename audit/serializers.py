from rest_framework import serializers

from audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor_user",
            "entity_type",
            "entity_id",
            "action",
            "old_values_json",
            "new_values_json",
            "ip_address",
            "user_agent",
            "created_at",
        )

from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "channel",
            "notification_type",
            "title",
            "body",
            "entity_type",
            "entity_id",
            "status",
            "sent_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "channel",
            "notification_type",
            "title",
            "body",
            "entity_type",
            "entity_id",
            "sent_at",
            "created_at",
        )

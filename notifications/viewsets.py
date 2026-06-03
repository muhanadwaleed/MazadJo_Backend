from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.models import Notification
from notifications.serializers import NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    @action(detail=True, methods=["patch"], url_path="read")
    def read(self, request, pk=None):
        obj = self.get_object()
        if obj.user_id != request.user.id:
            return Response(status=403)
        obj.status = Notification.Status.READ
        obj.save(update_fields=["status"])
        return Response(NotificationSerializer(obj).data)

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsStaffUser
from payments.models import PaymentTransaction
from subscriptions.models import AuctionSubscription
from subscriptions.serializers import (
    AuctionSubscriptionCreateSerializer,
    AuctionSubscriptionSerializer,
)


class AuctionSubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = AuctionSubscription.objects.all().select_related("auction", "user")
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return AuctionSubscriptionCreateSerializer
        return AuctionSubscriptionSerializer

    @action(
        detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsStaffUser]
    )
    def mark_paid(self, request, pk=None):
        obj = self.get_object()
        if obj.status != AuctionSubscription.Status.PENDING_PAYMENT:
            return Response(
                {"detail": "Invalid subscription status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.status = AuctionSubscription.Status.ACTIVE
        obj.payment_status = AuctionSubscription.PaymentStatus.PAID
        obj.activated_at = timezone.now()
        obj.save(
            update_fields=["status", "payment_status", "activated_at", "updated_at"]
        )
        now = timezone.now()
        PaymentTransaction.objects.filter(
            related_entity_type=PaymentTransaction.RelatedEntityType.SUBSCRIPTION,
            related_entity_id=obj.id,
        ).update(
            status=PaymentTransaction.PaymentStatus.SUCCEEDED,
            completed_at=now,
        )
        return Response(AuctionSubscriptionSerializer(obj).data)

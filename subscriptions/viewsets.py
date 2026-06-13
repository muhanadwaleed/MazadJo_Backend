from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from subscriptions.models import AuctionSubscription
from subscriptions.serializers import (
    AuctionSubscriptionCreateSerializer,
    AuctionSubscriptionSerializer,
)
from subscriptions.services import complete_subscription_payment


class AuctionSubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = AuctionSubscriptionSerializer

    def get_queryset(self):
        qs = AuctionSubscription.objects.all().select_related(
            "auction", "user", "auction__seller"
        )
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        auction_id = self.request.query_params.get("auction")
        if auction_id:
            qs = qs.filter(auction_id=auction_id)
        sub_status = self.request.query_params.get("status")
        if sub_status:
            qs = qs.filter(status=sub_status)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return AuctionSubscriptionCreateSerializer
        return AuctionSubscriptionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub = serializer.save()
        out = AuctionSubscriptionSerializer(sub, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        obj = self.get_object()
        if obj.status == AuctionSubscription.Status.ACTIVE:
            return Response(
                AuctionSubscriptionSerializer(obj, context={"request": request}).data
            )
        if obj.status != AuctionSubscription.Status.PENDING_PAYMENT:
            return Response(
                {"detail": "Invalid subscription status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        complete_subscription_payment(obj, request=request)
        obj.refresh_from_db()
        return Response(
            AuctionSubscriptionSerializer(obj, context={"request": request}).data
        )

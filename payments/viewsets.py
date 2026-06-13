from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from payments.models import PaymentTransaction
from payments.serializers import PaymentTransactionSerializer


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = PaymentTransaction.objects.all().order_by("-initiated_at")
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        auction_id = self.request.query_params.get("auction")
        if auction_id:
            from subscriptions.models import AuctionSubscription

            sub_ids = AuctionSubscription.objects.filter(
                auction_id=auction_id
            ).values_list("id", flat=True)
            qs = qs.filter(
                related_entity_type=PaymentTransaction.RelatedEntityType.SUBSCRIPTION,
                related_entity_id__in=sub_ids,
            )
        return qs

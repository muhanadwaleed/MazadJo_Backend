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
        return qs

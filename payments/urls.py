from django.urls import include, path
from rest_framework.routers import DefaultRouter

from payments.viewsets import PaymentTransactionViewSet
from payments.webhook import PaymentWebhookView

router = DefaultRouter()
router.register(
    r"payments/transactions",
    PaymentTransactionViewSet,
    basename="payment-transaction",
)

urlpatterns = [
    path("webhooks/payments/", PaymentWebhookView.as_view(), name="payment-webhook"),
    path("", include(router.urls)),
]

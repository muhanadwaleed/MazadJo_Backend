from django.urls import include, path
from rest_framework.routers import DefaultRouter

from subscriptions.viewsets import AuctionSubscriptionViewSet

router = DefaultRouter()
router.register(r"subscriptions", AuctionSubscriptionViewSet, basename="subscription")

urlpatterns = [
    path("", include(router.urls)),
]

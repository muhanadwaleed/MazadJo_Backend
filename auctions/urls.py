from django.urls import include, path
from rest_framework.routers import DefaultRouter

from auctions.viewsets import AuctionViewSet, WatchlistViewSet

router = DefaultRouter()
router.register(r"auctions", AuctionViewSet, basename="auction")
router.register(r"watchlist", WatchlistViewSet, basename="watchlist")

urlpatterns = [
    path("", include(router.urls)),
]

"""WebSocket URL patterns for Django Channels."""

from django.urls import path

from auctions.consumers import AuctionConsumer

websocket_urlpatterns = [
    path("ws/auctions/<int:auction_id>/", AuctionConsumer.as_asgi()),
]

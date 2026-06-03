import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from auctions.models import Auction

User = get_user_model()


@database_sync_to_async
def _user_from_access_token(token: str):
    try:
        tok = AccessToken(token)
        return User.objects.get(pk=tok["user_id"])
    except (TokenError, InvalidToken, User.DoesNotExist, KeyError):
        return None


@database_sync_to_async
def _user_may_connect_auction(user, auction_id: int) -> bool:
    if not user.is_active:
        return False
    try:
        auction = Auction.objects.get(pk=auction_id)
    except Auction.DoesNotExist:
        return False
    if auction.status == Auction.Status.CANCELLED:
        return False
    return True


class AuctionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.auction_id = self.scope["url_route"]["kwargs"]["auction_id"]
        raw_qs = self.scope.get("query_string") or b""
        token = (parse_qs(raw_qs.decode()).get("token") or [""])[0]
        if not token:
            await self.close(code=4401)
            return
        user = await _user_from_access_token(token)
        if not user:
            await self.close(code=4401)
            return
        if not await _user_may_connect_auction(user, self.auction_id):
            await self.close(code=4403)
            return
        self.group_name = f"auction_{self.auction_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        from observability.metrics import ws_connect

        ws_connect()
        self._metrics_ws_counted = True

    async def disconnect(self, close_code):
        if getattr(self, "_metrics_ws_counted", False):
            from observability.metrics import ws_disconnect

            ws_disconnect()
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def auction_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))

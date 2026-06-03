import json
from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_auction_event(auction_id: int, data: dict) -> None:
    layer = get_channel_layer()
    if not layer:
        return
    payload = {}
    for k, v in data.items():
        if isinstance(v, Decimal):
            payload[k] = str(v)
        else:
            payload[k] = v
    async_to_sync(layer.group_send)(
        f"auction_{auction_id}",
        {"type": "auction.message", "data": payload},
    )

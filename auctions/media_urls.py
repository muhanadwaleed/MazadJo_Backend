"""Build serve URLs for auction media (binary stored in DB)."""


def auction_media_serve_path(auction_id: int, media_id: int) -> str:
    return f"/api/v1/auctions/{auction_id}/media/{media_id}/"


def auction_media_serve_url(auction_id: int, media_id: int, request=None) -> str:
    path = auction_media_serve_path(auction_id, media_id)
    if request is not None:
        return request.build_absolute_uri(path)
    return path

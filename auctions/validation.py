"""ProductSettings-driven validation for auction drafts."""

from __future__ import annotations

import os
from decimal import Decimal

from rest_framework.exceptions import ValidationError as DRFValidationError

from auctions.models import Auction, AuctionMedia
from catalog.models import ProductSettings


def get_product_settings(auction: Auction) -> ProductSettings:
    try:
        return auction.product_category.settings
    except ProductSettings.DoesNotExist as exc:
        raise DRFValidationError(
            {"product_category": "Category has no product settings."}
        ) from exc


def _normalize_extension(file_name: str) -> str:
    _, ext = os.path.splitext(file_name or "")
    return ext.lower()


def _extension_allowed(file_name: str, allowed: list) -> bool:
    if not allowed:
        return True
    ext = _normalize_extension(file_name)
    normalized = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in allowed}
    return ext in normalized


def validate_auction_fields(
    auction: Auction,
    *,
    settings: ProductSettings | None = None,
    require_media: bool = False,
) -> None:
    """
    Raise DRF ValidationError with field-keyed messages when rules fail.

    ``require_media`` is True on submit when min_images_count must be satisfied.
    """
    settings = settings or get_product_settings(auction)
    errors: dict[str, list[str]] = {}

    if auction.start_price < settings.min_start_price:
        errors.setdefault("start_price", []).append(
            f"Start price must be at least {settings.min_start_price}."
        )

    if settings.reserve_price_required and auction.reserve_price is None:
        errors.setdefault("reserve_price", []).append(
            "Reserve price is required for this category."
        )

    if settings.location_link_enabled and not (auction.location_link or "").strip():
        errors.setdefault("location_link", []).append(
            "Location link is required for this category."
        )

    if require_media:
        images = auction.media_items.filter(media_type=AuctionMedia.MediaType.IMAGE)
        image_count = images.count()
        if image_count < settings.min_images_count:
            errors.setdefault("media_items", []).append(
                f"At least {settings.min_images_count} image(s) required "
                f"(currently {image_count})."
            )
        if image_count > settings.max_images_count:
            errors.setdefault("media_items", []).append(
                f"At most {settings.max_images_count} image(s) allowed "
                f"(currently {image_count})."
            )

        videos = auction.media_items.filter(media_type=AuctionMedia.MediaType.VIDEO)
        if videos.exists() and not settings.video_allowed:
            errors.setdefault("media_items", []).append(
                "Video is not allowed for this category."
            )

        if settings.allowed_extensions_json:
            for media in auction.media_items.all():
                if not _extension_allowed(
                    media.file_name, settings.allowed_extensions_json
                ):
                    errors.setdefault("media_items", []).append(
                        f"File extension not allowed: {media.file_name}"
                    )
                    break

    if errors:
        raise DRFValidationError(errors)


def validate_media_upload(
    auction: Auction,
    *,
    media_type: str,
    file_name: str,
    file_size: int,
    is_blurred: bool = False,
    max_bytes: int,
) -> None:
    """Validate a single media upload against category rules and size limits."""
    settings = get_product_settings(auction)
    errors: dict[str, list[str]] = {}

    if file_size > max_bytes:
        errors.setdefault("file", []).append(
            f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB."
        )

    if media_type == AuctionMedia.MediaType.VIDEO and not settings.video_allowed:
        errors.setdefault("media_type", []).append(
            "Video is not allowed for this category."
        )

    if media_type == AuctionMedia.MediaType.FILE and not settings.attachments_allowed:
        errors.setdefault("media_type", []).append(
            "Attachments are not allowed for this category."
        )

    if is_blurred and not settings.blur_option_enabled:
        errors.setdefault("is_blurred", []).append(
            "Blur option is not enabled for this category."
        )

    if settings.allowed_extensions_json and not _extension_allowed(
        file_name, settings.allowed_extensions_json
    ):
        errors.setdefault("file", []).append(
            f"File extension not allowed. Allowed: {settings.allowed_extensions_json}"
        )

    if media_type == AuctionMedia.MediaType.IMAGE:
        current_images = auction.media_items.filter(
            media_type=AuctionMedia.MediaType.IMAGE
        ).count()
        if current_images >= settings.max_images_count:
            errors.setdefault("media_type", []).append(
                f"Maximum {settings.max_images_count} image(s) reached."
            )

    if errors:
        raise DRFValidationError(errors)


def default_min_bid_increment(category) -> Decimal:
    settings = ProductSettings.objects.filter(category=category).first()
    if settings is None:
        return Decimal("1")
    return settings.min_bid_increment


# Seller may cancel before the auction goes live (no staff cancel path).
SELLER_CANCELLABLE_STATUSES = (
    Auction.Status.DRAFT,
    Auction.Status.RETURNED_FOR_EDIT,
    Auction.Status.UNDER_REVIEW,
    Auction.Status.APPROVED,
    Auction.Status.SCHEDULED,
)


def validate_publish_schedule(auction: Auction) -> None:
    """Ensure schedule is valid when staff publishes an approved auction."""
    errors: dict[str, list[str]] = {}

    if auction.ends_at <= auction.starts_at:
        errors.setdefault("ends_at", []).append(
            "End time must be after start time."
        )

    if errors:
        raise DRFValidationError(errors)

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.stats import increment_user_public_bid_count
from auctions.models import Auction
from auctions.realtime import broadcast_auction_event
from auctions.services import maybe_close_auction
from bidding.abuse import (
    assert_bid_rate_allowed,
    assert_not_shadow_banned_user_id,
    bid_suppressed_for_user,
)
from bidding.models import AuctionPriceSnapshot, Bid, BidIdempotency
from bidding.utils import mask_username
from catalog.models import ProductSettings
from fraud.utils import detect_self_outbidding_chain
from subscriptions.models import AuctionSubscription

logger = logging.getLogger("mazadjo.bids")


def _maybe_extend_auction_end(
    auction: Auction,
    now,
    ps: ProductSettings | None,
) -> tuple[bool, datetime | None]:
    """If anti-sniping applies, extend deadline fields (row already locked)."""
    if not ps or not ps.auction_extension_enabled:
        return False, None
    remaining_sec = (auction.ends_at - now).total_seconds()
    if remaining_sec <= 0:
        return False, None
    force_sec = int(getattr(settings, "ANTI_SNIPE_FORCE_SECONDS", 10))
    in_trigger_window = remaining_sec <= ps.extension_trigger_seconds
    in_force_window = remaining_sec < force_sec
    if not in_trigger_window and not in_force_window:
        return False, None
    prev = auction.ends_at
    extend_minutes = ps.extension_minutes
    auction.ends_at = prev + timedelta(minutes=extend_minutes)
    auction.extend_deadline = auction.ends_at
    auction.extension_count += 1
    auction.save(update_fields=["ends_at", "extend_deadline", "extension_count", "updated_at"])
    return True, prev


def _for_update_kwargs():
    if connection.vendor == "postgresql":
        return {"of": ("self",)}
    return {}


@transaction.atomic
def place_bid(
    *,
    auction_id: int,
    user_id: int,
    amount: Decimal,
    bid_source: str,
    idempotency_key: str | None = None,
) -> Bid:
    auction = (
        Auction.objects.select_related("product_category__settings", "seller")
        .select_for_update(**_for_update_kwargs())
        .get(pk=auction_id)
    )
    if maybe_close_auction(auction):
        auction.refresh_from_db()
    now = timezone.now()
    if auction.starts_at > now:
        raise ValidationError("Auction has not started yet.")
    if auction.ends_at < now:
        raise ValidationError("Auction is not open for bidding.")
    if auction.status in (
        Auction.Status.CANCELLED,
        Auction.Status.CLOSED,
        Auction.Status.ENDED,
        Auction.Status.ENDED_WITHOUT_BIDS,
    ):
        raise ValidationError("Auction is not accepting bids.")
    if auction.status == Auction.Status.SCHEDULED:
        auction.status = Auction.Status.ACTIVE
        auction.save(update_fields=["status", "updated_at"])
    if auction.status != Auction.Status.ACTIVE:
        raise ValidationError("Auction is not active.")

    if idempotency_key:
        key = idempotency_key.strip()[:128]
        if not key:
            raise ValidationError("Idempotency-Key cannot be empty.")
        existing = (
            BidIdempotency.objects.filter(
                auction_id=auction_id, user_id=user_id, key=key
            )
            .select_related("bid")
            .first()
        )
        if existing:
            return existing.bid

    assert_not_shadow_banned_user_id(user_id)
    silent_shadow = getattr(settings, "SHADOW_BID_SILENT_PUBLICATION", True)
    suppress = bid_suppressed_for_user(user_id) if silent_shadow else False
    assert_bid_rate_allowed(user_id=user_id, auction_id=auction_id)

    ps = getattr(auction.product_category, "settings", None)
    extension_applied = False
    if not suppress:
        extension_applied, _ = _maybe_extend_auction_end(auction, now, ps)
        if extension_applied:
            now = timezone.now()
            if auction.ends_at < now:
                raise ValidationError("Auction is not open for bidding.")

    try:
        sub = AuctionSubscription.objects.select_for_update(**_for_update_kwargs()).get(
            auction_id=auction_id,
            user_id=user_id,
            status=AuctionSubscription.Status.ACTIVE,
        )
    except AuctionSubscription.DoesNotExist as e:
        raise ValidationError("Active subscription required to bid.") from e

    if amount <= auction.current_price:
        logger.warning(
            "bid_rejected reason=below_current auction_id=%s user_id=%s",
            auction_id,
            user_id,
        )
        _metrics_reject("below_current")
        raise ValidationError("Bid must be higher than the current price.")
    increment = amount - auction.current_price
    if increment < auction.min_bid_increment:
        logger.warning(
            "bid_rejected reason=min_increment auction_id=%s user_id=%s increment=%s min=%s",
            auction_id,
            user_id,
            increment,
            auction.min_bid_increment,
        )
        _metrics_reject("min_increment")
        raise ValidationError(
            f"Minimum increment is {auction.min_bid_increment} (required total "
            f"{auction.current_price + auction.min_bid_increment})."
        )

    bump_self = int(getattr(settings, "RISK_SELF_OUTBID_BUMP", 0))
    min_run = int(getattr(settings, "RISK_SELF_OUTBID_MIN_PRIOR_RUN", 2))
    if bump_self > 0 and detect_self_outbidding_chain(
        user_id=user_id, auction_id=auction_id, min_prior_run=min_run
    ):
        from accounts.models import UserRiskScore

        r, _ = UserRiskScore.objects.get_or_create(user_id=user_id)
        r.increase(bump_self)
        logger.info(
            "fraud_signal self_outbid_chain auction_id=%s user_id=%s bump=%s score=%s",
            auction_id,
            user_id,
            bump_self,
            r.score,
        )

    if not suppress:
        Bid.objects.filter(
            auction=auction,
            status=Bid.Status.ACCEPTED,
            suppress_publication=False,
        ).update(status=Bid.Status.OUTBID)

    bid = Bid.objects.create(
        auction=auction,
        bidder_id=user_id,
        subscription=sub,
        amount=amount,
        increment_amount=amount - auction.current_price,
        bid_source=bid_source,
        status=Bid.Status.ACCEPTED,
        is_highest_at_time=not suppress,
        suppress_publication=suppress,
    )
    if idempotency_key:
        key = idempotency_key.strip()[:128]
        BidIdempotency.objects.create(
            auction_id=auction_id,
            user_id=user_id,
            key=key,
            bid=bid,
        )

    if not suppress:
        prev_price = auction.current_price
        auction.current_price = amount
        auction.save(update_fields=["current_price", "updated_at"])
        AuctionPriceSnapshot.objects.create(
            auction=auction,
            bid=bid,
            previous_price=prev_price,
            new_price=amount,
            event_type=AuctionPriceSnapshot.EventType.BID,
        )
        increment_user_public_bid_count(user_id=user_id)

    def _after_bid_commit():
        if suppress:
            return
        from django.contrib.auth import get_user_model

        bidder = get_user_model().objects.filter(pk=user_id).only("username").first()
        label = mask_username(bidder.username) if bidder else "***"
        broadcast_auction_event(
            auction_id,
            {
                "type": "bid_placed",
                "auction_id": auction_id,
                "bid_id": bid.id,
                "current_price": auction.current_price,
                "bidder": label,
                "ends_at": auction.ends_at.isoformat(),
                "extension_applied": extension_applied,
            },
        )
        if getattr(settings, "FRAUD_ANALYZE_BID_ASYNC", True):
            from fraud.tasks import analyze_bid_fraud

            analyze_bid_fraud.delay(bid.id)

    transaction.on_commit(_after_bid_commit)
    if suppress:
        logger.info(
            "shadow_bid_accepted auction_id=%s user_id=%s bid_id=%s amount=%s",
            auction_id,
            user_id,
            bid.id,
            amount,
        )
        _metrics_shadow_bid()
    else:
        logger.info(
            "bid_placed auction_id=%s user_id=%s bid_id=%s amount=%s",
            auction_id,
            user_id,
            bid.id,
            amount,
        )
        _metrics_placed()
    return bid


def _metrics_reject(reason: str) -> None:
    from observability.metrics import record_bid_rejected

    record_bid_rejected(reason)


def _metrics_placed() -> None:
    from observability.metrics import record_bid_placed

    record_bid_placed()


def _metrics_shadow_bid() -> None:
    from observability.metrics import record_fraud_flag

    record_fraud_flag("shadow_bid")

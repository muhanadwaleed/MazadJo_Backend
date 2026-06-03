"""
Fraud heuristics (measurable; thresholds live in Django settings / .env).

Uses ``Bid.bidder`` (not ``user``) to match this project's schema.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from bidding.models import Bid


def get_user_bid_count_last_seconds(*, user_id: int, seconds: int | None = None) -> int:
    window = int(
        seconds
        if seconds is not None
        else getattr(settings, "BID_VELOCITY_WINDOW_SEC", 1)
    )
    since = timezone.now() - timedelta(seconds=max(window, 1))
    return Bid.objects.filter(
        bidder_id=user_id,
        created_at__gte=since,
        status=Bid.Status.ACCEPTED,
    ).count()


def _public_bids_qs(**filters):
    return Bid.objects.filter(suppress_publication=False, **filters)


def consecutive_accepted_bids_by_user(
    *, user_id: int, auction_id: int, limit: int = 10
) -> int:
    """How many most recent accepted bids on this auction are from this user (stops at first other bidder)."""
    run = 0
    qs = _public_bids_qs(auction_id=auction_id, status=Bid.Status.ACCEPTED).order_by(
        "-created_at"
    )[:limit]
    for b in qs:
        if b.bidder_id == user_id:
            run += 1
        else:
            break
    return run


def detect_self_outbidding_chain(
    *, user_id: int, auction_id: int, min_prior_run: int = 2
) -> bool:
    """
    True if this user already has ``min_prior_run`` consecutive top bids on the auction
    (so the next bid would extend a self-only chain to min_prior_run + 1).
    """
    prior = consecutive_accepted_bids_by_user(user_id=user_id, auction_id=auction_id)
    return prior >= min_prior_run


def detect_bid_pumping(*, auction_id: int) -> bool:
    """
    Detect alternating two-bidder pattern on the last six *public* accepted bids
    within a short wall-clock window (oldest → newest).

    Example user ids oldest-first: [a, b, a, b, a, b] with a != b.
    """
    now = timezone.now()
    window_sec = int(getattr(settings, "RISK_PUMPING_WINDOW_SECONDS", 15))
    since = now - timedelta(seconds=max(window_sec, 1))
    last = list(
        _public_bids_qs(
            auction_id=auction_id,
            status=Bid.Status.ACCEPTED,
            created_at__gte=since,
        ).order_by("-created_at")[:6]
    )
    if len(last) < 6:
        return False
    oldest_first = [b.bidder_id for b in reversed(last)]
    if len(set(oldest_first)) != 2:
        return False
    a, b = oldest_first[0], oldest_first[1]
    if a == b:
        return False
    expected = [a, b, a, b, a, b]
    return oldest_first == expected

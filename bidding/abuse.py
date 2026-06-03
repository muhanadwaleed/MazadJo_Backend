import logging
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied, Throttled

logger = logging.getLogger("mazadjo.bids")


def _risk_shadow_threshold_hit(user_id: int) -> bool:
    """True when risk-score shadow is enabled and the user's score is at/above the threshold."""
    if not getattr(settings, "RISK_ENFORCE_SHADOW_FROM_SCORE", False):
        return False
    from accounts.models import UserRiskScore

    threshold = int(getattr(settings, "RISK_SHADOW_BAN_SCORE", 50))
    score = (
        UserRiskScore.objects.filter(user_id=user_id)
        .values_list("score", flat=True)
        .first()
    )
    return score is not None and score >= threshold


def bid_suppressed_for_user(user_id: int) -> bool:
    """
    True if this user's bids should be accepted silently (no public feed / no price move).

    Staff ``User.is_shadow_banned`` always suppresses when silent mode is on.
    Risk-score shadow only applies when ``RISK_ENFORCE_SHADOW_FROM_SCORE`` is True.
    """
    User = get_user_model()
    if User.objects.filter(pk=user_id, is_shadow_banned=True).exists():
        return True
    return _risk_shadow_threshold_hit(user_id)


def assert_not_shadow_banned_user_id(user_id: int) -> None:
    """
    Hard reject for shadow / risk-shadow when ``SHADOW_BID_SILENT_PUBLICATION`` is False.

    When silent mode is True, this does not raise (use ``bid_suppressed_for_user`` in ``place_bid``).
    """
    if getattr(settings, "SHADOW_BID_SILENT_PUBLICATION", True):
        return
    User = get_user_model()
    banned = (
        User.objects.filter(pk=user_id)
        .values_list("is_shadow_banned", flat=True)
        .first()
    )
    if banned:
        logger.warning("bid_shadow_banned user_id=%s", user_id)
        from observability.metrics import record_bid_rejected

        record_bid_rejected("shadow_ban")
        raise PermissionDenied(detail="Bid could not be processed.")
    if _risk_shadow_threshold_hit(user_id):
        logger.warning("bid_risk_shadow user_id=%s", user_id)
        from observability.metrics import record_bid_rejected

        record_bid_rejected("risk_shadow")
        raise PermissionDenied(detail="Bid could not be processed.")


def assert_bid_rate_allowed(*, user_id: int, auction_id: int) -> None:
    max_per_sec = int(getattr(settings, "BID_MAX_PER_SECOND_PER_USER", 3))
    if max_per_sec <= 0:
        return
    sec = int(time.time())
    k = f"bid:rl:{user_id}:{auction_id}:{sec}"
    if cache.add(k, 1, timeout=3):
        n = 1
    else:
        try:
            n = cache.incr(k)
        except ValueError:
            cache.set(k, 1, timeout=3)
            n = 1
    if n > max_per_sec:
        bump = int(getattr(settings, "RISK_RATE_LIMIT_CACHE_BUMP", 0))
        if bump > 0:
            try:
                from accounts.models import UserRiskScore

                r, _ = UserRiskScore.objects.get_or_create(user_id=user_id)
                r.increase(bump)
                logger.info(
                    "risk_bump_on_rate_limit user_id=%s bump=%s score=%s",
                    user_id,
                    bump,
                    r.score,
                )
            except Exception:
                logger.exception("risk_bump_on_rate_limit_failed user_id=%s", user_id)
        logger.warning(
            "bid_rate_limited auction_id=%s user_id=%s count=%s",
            auction_id,
            user_id,
            n,
        )
        from observability.metrics import record_bid_rejected

        record_bid_rejected("rate_limit")
        raise Throttled(detail="Too many bids. Slow down.")

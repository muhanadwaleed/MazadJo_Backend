import logging

from celery import shared_task
from django.conf import settings
from django.db.models import F, Value
from django.db.models.functions import Greatest

from accounts.models import UserFingerprint, UserRiskScore, UserStats
from auctions.models import Auction
from bidding.models import Bid
from observability.metrics import record_fraud_flag, record_fraud_score_observed

logger = logging.getLogger("mazadjo.fraud")


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def analyze_bid_fraud(self, bid_id: int) -> None:
    """
    Async scoring after a public (non-suppressed) accepted bid.
    """
    try:
        bid = Bid.objects.select_related("bidder", "auction").get(pk=bid_id)
    except Bid.DoesNotExist:
        return

    if bid.suppress_publication:
        return

    user = bid.bidder
    auction = bid.auction
    risk, _ = UserRiskScore.objects.get_or_create(user=user)

    from fraud.utils import detect_bid_pumping

    if detect_bid_pumping(auction_id=auction.id):
        bump = int(getattr(settings, "RISK_PUMPING_BUMP", 20))
        if bump:
            risk.increase(bump)
            logger.info(
                "fraud_signal bid_pumping bid_id=%s auction_id=%s bump=%s score=%s",
                bid_id,
                auction.id,
                bump,
                risk.score,
            )
            record_fraud_flag("bid_pumping")

    user_ips = list(
        UserFingerprint.objects.filter(user_id=user.id)
        .exclude(ip_address__isnull=True)
        .exclude(ip_address="")
        .values_list("ip_address", flat=True)
        .distinct()[:50]
    )
    if user_ips:
        other_accounts = (
            UserFingerprint.objects.filter(ip_address__in=user_ips)
            .exclude(user_id=user.id)
            .values("user_id")
            .distinct()
            .count()
        )
        threshold = int(getattr(settings, "RISK_SHARED_IP_ACCOUNT_THRESHOLD", 3))
        bump_ip = int(getattr(settings, "RISK_SHARED_IP_BUMP", 30))
        if other_accounts > threshold and bump_ip:
            risk.increase(bump_ip)
            logger.info(
                "fraud_signal shared_ip bid_id=%s other_accounts=%s bump=%s score=%s",
                bid_id,
                other_accounts,
                bump_ip,
                risk.score,
            )
            record_fraud_flag("shared_ip")

    stats, _ = UserStats.objects.get_or_create(user_id=user.id)
    total = int(stats.total_bids)
    wins = int(stats.total_wins)
    if getattr(settings, "RISK_STATS_FALLBACK_WHEN_ZERO", True) and total == 0:
        total = Bid.objects.filter(
            bidder_id=user.id, suppress_publication=False
        ).count()
        wins = Auction.objects.filter(winner_user_id=user.id).count()
        UserStats.objects.filter(pk=stats.pk).update(total_bids=total, total_wins=wins)

    min_bids = int(getattr(settings, "RISK_WIN_RATIO_MIN_TOTAL_BIDS", 10))
    ratio_limit = float(getattr(settings, "RISK_WIN_RATIO_THRESHOLD", 0.8))
    bump_win = int(getattr(settings, "RISK_WIN_RATIO_BUMP", 15))
    if total > min_bids and wins / total > ratio_limit and bump_win:
        risk.increase(bump_win)
        logger.info(
            "fraud_signal win_ratio bid_id=%s wins=%s total=%s bump=%s score=%s",
            bid_id,
            wins,
            total,
            bump_win,
            risk.score,
        )
        record_fraud_flag("win_ratio")

    risk.refresh_from_db()
    record_fraud_score_observed(risk.score)

    hard_at = int(getattr(settings, "RISK_HARD_BAN_SCORE", 80))
    if risk.score >= hard_at and getattr(
        settings, "RISK_ENFORCE_HARD_DEACTIVATE", False
    ):
        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])
            logger.warning(
                "fraud_enforce hard_deactivate user_id=%s score=%s bid_id=%s",
                user.id,
                risk.score,
                bid_id,
            )


@shared_task
def decay_risk_scores() -> None:
    """
    Periodically reduce stored risk scores so users are not flagged forever.

    ``RISK_DECAY_MODE``: ``linear`` (subtract points, floored at 0) or ``multiply``.
    """
    if not getattr(settings, "RISK_DECAY_ENABLED", True):
        return

    mode = getattr(settings, "RISK_DECAY_MODE", "linear").strip().lower()
    if mode == "multiply":
        factor = float(getattr(settings, "RISK_DECAY_MULTIPLY_FACTOR", 0.95))
        qs = UserRiskScore.objects.filter(score__gt=0).only("id", "score")
        for row in qs.iterator(chunk_size=500):
            new_score = int(row.score * factor)
            if new_score != row.score:
                UserRiskScore.objects.filter(pk=row.pk).update(score=new_score)
    else:
        pts = int(getattr(settings, "RISK_DECAY_LINEAR_POINTS", 1))
        if pts <= 0:
            return
        UserRiskScore.objects.filter(score__gt=0).update(
            score=Greatest(F("score") - pts, Value(0)),
        )

    record_fraud_flag("risk_decay_tick")

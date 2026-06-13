from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from auctions.models import Auction, AuctionReviewLog
from auctions.validation import SELLER_CANCELLABLE_STATUSES
from audit.services import log_audit
from configuration.services.review_checklist import validate_review_checklist_complete


def maybe_close_auction(auction: Auction) -> bool:
    if auction.ends_at is None:
        return False
    now = timezone.now()
    if auction.ends_at >= now:
        return False
    from bidding.models import Bid

    if auction.status == Auction.Status.ACTIVE:
        has_bids = Bid.objects.filter(
            auction=auction, suppress_publication=False
        ).exists()
        auction.status = (
            Auction.Status.ENDED if has_bids else Auction.Status.ENDED_WITHOUT_BIDS
        )
        auction.actual_end_at = now
        auction.save(update_fields=["status", "actual_end_at", "updated_at"])
        return True
    if auction.status == Auction.Status.SCHEDULED:
        auction.status = Auction.Status.ENDED_WITHOUT_BIDS
        auction.actual_end_at = now
        auction.save(update_fields=["status", "actual_end_at", "updated_at"])
        return True
    return False


def on_auction_entered_review(auction: Auction) -> None:
    from configuration.services.review_checklist import ensure_auction_review_checklist

    ensure_auction_review_checklist(auction)


def perform_staff_review(
    auction: Auction,
    *,
    reviewer,
    decision: str,
    reason: str = "",
    request=None,
) -> Auction:
    if auction.status != Auction.Status.UNDER_REVIEW:
        raise DRFValidationError({"status": ["Auction is not under review."]})

    if decision == AuctionReviewLog.Decision.APPROVE:
        validate_review_checklist_complete(auction)

    old_status = auction.status
    AuctionReviewLog.objects.create(
        auction=auction,
        reviewer=reviewer,
        decision=decision,
        reason=reason,
    )

    if decision == AuctionReviewLog.Decision.APPROVE:
        auction.status = Auction.Status.APPROVED
    elif decision == AuctionReviewLog.Decision.REJECT:
        auction.status = Auction.Status.REJECTED
    else:
        auction.status = Auction.Status.RETURNED_FOR_EDIT

    auction.save(update_fields=["status", "updated_at"])
    log_audit(
        actor=reviewer,
        entity_type="auction",
        entity_id=auction.id,
        action=f"staff_review_{decision}",
        old_values={"status": old_status},
        new_values={"status": auction.status, "reason": reason},
        request=request,
    )
    return auction


def perform_seller_cancel(
    auction: Auction,
    *,
    seller,
    reason: str = "",
    request=None,
) -> Auction:
    if auction.seller_id != seller.id:
        raise DRFValidationError({"detail": "Only the listing owner can cancel."})

    if auction.status not in SELLER_CANCELLABLE_STATUSES:
        raise DRFValidationError(
            {"status": ["Auction cannot be cancelled in its current state."]}
        )

    old_status = auction.status
    auction.status = Auction.Status.CANCELLED
    auction.save(update_fields=["status", "updated_at"])

    log_audit(
        actor=seller,
        entity_type="auction",
        entity_id=auction.id,
        action="seller_cancel",
        old_values={"status": old_status},
        new_values={"status": auction.status, "reason": reason},
        request=request,
    )
    return auction

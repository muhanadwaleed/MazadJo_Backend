"""Auction list/detail visibility rules for public vs staff vs seller."""

from django.db.models import Q, QuerySet

from auctions.models import Auction

# Statuses visible on the public browse catalog (no auth required).
PUBLIC_BROWSE_STATUSES = (
    Auction.Status.SCHEDULED,
    Auction.Status.ACTIVE,
    Auction.Status.ENDED,
    Auction.Status.ENDED_WITHOUT_BIDS,
    Auction.Status.DELIVERY_IN_PROGRESS,
    Auction.Status.CLOSED,
    Auction.Status.CANCELLED,
)

DETAIL_ACTIONS = frozenset(
    {
        "retrieve",
        "bids",
        "update",
        "partial_update",
        "submit",
        "watchlist",
        "staff_review",
        "staff_publish",
        "review_checklist",
        "media_upload",
        "media_detail",
        "cancel",
    }
)

# Draft-like statuses where only owner/staff may view listing + media.
PRE_PUBLISH_STATUSES = (
    Auction.Status.DRAFT,
    Auction.Status.UNDER_REVIEW,
    Auction.Status.RETURNED_FOR_EDIT,
    Auction.Status.REJECTED,
    Auction.Status.APPROVED,
)


def _is_truthy_mine(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes")


def _apply_status_filter(
    qs: QuerySet[Auction], status: str | None, *, allow_any: bool
) -> QuerySet[Auction]:
    if not status:
        return qs
    if allow_any:
        return qs.filter(status=status)
    if status in PUBLIC_BROWSE_STATUSES:
        return qs.filter(status=status)
    return qs.none()


def filter_auctions_for_request(
    qs: QuerySet[Auction],
    *,
    user,
    action: str,
    status: str | None = None,
    mine: str | None = None,
) -> QuerySet[Auction]:
    """
    Apply visibility rules before category/search/seller filters.

    - ``mine=1``: authenticated seller's own rows (any status).
    - Staff: all rows; optional ``status`` filter.
    - List (browse): public statuses only unless staff / mine.
    - Detail: public rows, or staff sees all, or owner sees own.
    """
    is_authenticated = user.is_authenticated
    is_staff = is_authenticated and user.is_staff
    mine_filter = _is_truthy_mine(mine)

    if mine_filter:
        if not is_authenticated:
            return qs.none()
        qs = qs.filter(seller=user)
        return _apply_status_filter(qs, status, allow_any=True)

    if is_staff:
        return _apply_status_filter(qs, status, allow_any=True)

    if action in DETAIL_ACTIONS:
        if is_authenticated:
            qs = qs.filter(
                Q(status__in=PUBLIC_BROWSE_STATUSES) | Q(seller=user)
            )
        else:
            qs = qs.filter(status__in=PUBLIC_BROWSE_STATUSES)
        return _apply_status_filter(qs, status, allow_any=False)

    # list (public browse)
    qs = _apply_status_filter(qs, status, allow_any=False)
    if not status:
        qs = qs.filter(status__in=PUBLIC_BROWSE_STATUSES)
    return qs


def can_serve_auction_media(auction: Auction, user) -> bool:
    """Public for browseable auctions; owner/staff for pre-publish rows."""
    if auction.status in PUBLIC_BROWSE_STATUSES:
        return True
    if auction.status in PRE_PUBLISH_STATUSES:
        if user.is_authenticated and user.is_staff:
            return True
        if user.is_authenticated and auction.seller_id == user.id:
            return True
    return False


def can_edit_auction_media(auction: Auction, user) -> bool:
    """Owner may upload/delete media only in editable draft states."""
    if not user.is_authenticated:
        return False
    if auction.seller_id != user.id:
        return False
    return auction.status in (
        Auction.Status.DRAFT,
        Auction.Status.RETURNED_FOR_EDIT,
    )

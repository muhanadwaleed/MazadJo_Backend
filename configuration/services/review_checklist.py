from configuration.models import AuctionReviewChecklist, ProductCategoryChecklist


def ensure_auction_review_checklist(auction) -> int:
    """
    Snapshot category checklist templates onto the auction (idempotent).
    Returns the number of new rows created.
    """
    links = (
        ProductCategoryChecklist.objects.filter(
            category=auction.product_category,
            checklist_item__is_active=True,
        )
        .select_related("checklist_item")
        .order_by("sort_order", "checklist_item__sort_order")
    )
    created = 0
    for link in links:
        item = link.checklist_item
        _, was_created = AuctionReviewChecklist.objects.get_or_create(
            auction=auction,
            checklist_item_key=item.key,
            defaults={
                "checklist_item_label": item.label_en,
                "source_item": item,
            },
        )
        if was_created:
            created += 1
    return created


def validate_review_checklist_complete(auction) -> None:
    """
    Require every snapshotted checklist row to be checked before staff approval.

    Categories with no assigned checklist items skip this gate.
    """
    from rest_framework.exceptions import ValidationError as DRFValidationError

    items = AuctionReviewChecklist.objects.filter(auction=auction)
    if not items.exists():
        return

    unchecked = items.filter(is_checked=False).values_list(
        "checklist_item_key", flat=True
    )
    keys = list(unchecked)
    if keys:
        raise DRFValidationError(
            {
                "review_checklist": [
                    "All checklist items must be checked before approval. "
                    f"Unchecked: {', '.join(keys)}"
                ]
            }
        )

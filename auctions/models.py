from django.conf import settings
from django.db import models


class Auction(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        UNDER_REVIEW = "under_review", "Under Review"
        RETURNED_FOR_EDIT = "returned_for_edit", "Returned For Edit"
        REJECTED = "rejected", "Rejected"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"
        ENDED_WITHOUT_BIDS = "ended_without_bids", "Ended Without Bids"
        DELIVERY_IN_PROGRESS = "delivery_in_progress", "Delivery In Progress"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auctions_as_seller",
    )
    product_category = models.ForeignKey(
        "catalog.ProductCategory",
        on_delete=models.PROTECT,
        related_name="auctions",
    )
    auction_number = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    start_price = models.DecimalField(max_digits=12, decimal_places=2)
    current_price = models.DecimalField(max_digits=12, decimal_places=2)
    reserve_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    min_bid_increment = models.DecimalField(max_digits=12, decimal_places=2)
    area = models.ForeignKey(
        "catalog.Area",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="auctions",
    )
    location_link = models.URLField(max_length=1024, blank=True)
    duration_days = models.PositiveIntegerField(default=7)
    starts_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    origin_deadline = models.DateTimeField(null=True, blank=True)
    extend_deadline = models.DateTimeField(null=True, blank=True)
    actual_end_at = models.DateTimeField(null=True, blank=True)
    extension_count = models.PositiveSmallIntegerField(default=0)
    winner_bid = models.ForeignKey(
        "bidding.Bid",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_auctions",
    )
    winner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auctions_won",
    )
    participants_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    is_anonymous_bidding = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "auctions"
        indexes = [
            models.Index(fields=["status", "ends_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.auction_number} — {self.title}"


class AuctionMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        FILE = "file", "File"

    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="media_items"
    )
    media_type = models.CharField(max_length=16, choices=MediaType.choices)
    file_data = models.BinaryField()
    file_type = models.CharField(max_length=128)
    file_name = models.CharField(max_length=255, blank=True)
    is_blurred = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "auction_media"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.auction_id} {self.media_type}"


class AuctionWatchlist(models.Model):
    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="watchlist_entries"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auction_watchlist",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auction_watchlist"
        constraints = [
            models.UniqueConstraint(
                fields=["auction", "user"], name="uniq_watchlist_auction_user"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.auction_id}"


class AuctionShareLog(models.Model):
    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="share_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auction_shares",
    )
    channel = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auction_share_logs"

    def __str__(self) -> str:
        return f"share {self.auction_id} via {self.channel}"


class AuctionReviewLog(models.Model):
    class Decision(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        RETURN_FOR_EDIT = "return_for_edit", "Return For Edit"

    auction = models.ForeignKey(
        Auction,
        on_delete=models.CASCADE,
        related_name="review_logs",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="auction_reviews",
    )
    decision = models.CharField(max_length=32, choices=Decision.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auction_review_logs"

    def __str__(self) -> str:
        return f"{self.decision} on auction {self.auction_id}"

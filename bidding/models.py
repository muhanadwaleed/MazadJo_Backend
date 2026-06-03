from django.conf import settings
from django.db import models


class Bid(models.Model):
    class BidSource(models.TextChoices):
        MANUAL = "manual", "Manual"
        QUICK_INCREMENT = "quick_increment", "Quick Increment"

    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        OUTBID = "outbid", "Outbid"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="bids",
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bids",
    )
    subscription = models.ForeignKey(
        "subscriptions.AuctionSubscription",
        on_delete=models.PROTECT,
        related_name="bids",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    increment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    bid_source = models.CharField(max_length=32, choices=BidSource.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACCEPTED,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True)
    is_highest_at_time = models.BooleanField(default=False)
    suppress_publication = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Accepted for bidder only: hidden from public bid list and does not advance auction price.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "bids"
        indexes = [
            models.Index(fields=["auction", "-created_at", "-id"]),
        ]

    def __str__(self) -> str:
        return f"Bid {self.amount} on {self.auction_id}"


class BidIdempotency(models.Model):
    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="bid_idempotency_keys",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bid_idempotency_keys",
    )
    key = models.CharField(max_length=128)
    bid = models.ForeignKey(
        Bid,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bid_idempotency"
        constraints = [
            models.UniqueConstraint(
                fields=["auction", "user", "key"],
                name="uniq_bid_idempotency_auction_user_key",
            ),
        ]

    def __str__(self) -> str:
        return f"idempotency {self.auction_id}:{self.user_id}"


class AuctionPriceSnapshot(models.Model):
    class EventType(models.TextChoices):
        BID = "bid", "Bid"
        ROLLBACK = "rollback", "Rollback"
        MANUAL_ADJUSTMENT = "manual_adjustment", "Manual Adjustment"
        CLOSE = "close", "Close"

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="price_snapshots",
    )
    bid = models.ForeignKey(
        Bid,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="price_snapshots",
    )
    previous_price = models.DecimalField(max_digits=12, decimal_places=2)
    new_price = models.DecimalField(max_digits=12, decimal_places=2)
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auction_price_snapshots"
        indexes = [
            models.Index(fields=["auction", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.previous_price} -> {self.new_price}"



from django.conf import settings
from django.db import models


class AuctionSubscription(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending Payment"
        ACTIVE = "active", "Active"
        WITHDRAWN = "withdrawn", "Withdrawn"
        REFUNDED = "refunded", "Refunded"
        DISQUALIFIED = "disqualified", "Disqualified"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CONFISCATED = "confiscated", "Confiscated"

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auction_subscriptions",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    subscription_fee = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "auction_subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["auction", "user"], name="uniq_subscription_auction_user"
            ),
        ]
        indexes = [
            models.Index(fields=["auction", "status"]),
        ]

    def __str__(self) -> str:
        return f"Sub {self.user_id} -> auction {self.auction_id}"


class SubscriptionPayment(models.Model):
    subscription = models.ForeignKey(
        AuctionSubscription,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payment_transaction = models.ForeignKey(
        "payments.PaymentTransaction",
        on_delete=models.PROTECT,
        related_name="subscription_payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=64, blank=True)
    payment_status = models.CharField(max_length=32)
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_gateway_response_json = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "subscription_payments"

    def __str__(self) -> str:
        return f"Pay sub {self.subscription_id} {self.amount}"

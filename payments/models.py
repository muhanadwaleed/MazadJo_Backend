from django.conf import settings
from django.db import models


class PaymentTransaction(models.Model):
    class RelatedEntityType(models.TextChoices):
        SUBSCRIPTION = "subscription", "Subscription"
        AUCTION = "auction", "Auction"
        REFUND = "refund", "Refund"

    class TransactionType(models.TextChoices):
        CHARGE = "charge", "Charge"
        REFUND = "refund", "Refund"
        CONFISCATION = "confiscation", "Confiscation"
        COMMISSION = "commission", "Commission"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        REQUIRES_ACTION = "requires_action", "Requires Action"
        AUTHORIZED = "authorized", "Authorized"
        SUCCEEDED = "succeeded", "Succeeded"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
        DISPUTED = "disputed", "Disputed"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )
    related_entity_type = models.CharField(
        max_length=32,
        choices=RelatedEntityType.choices,
        db_index=True,
    )
    related_entity_id = models.BigIntegerField(db_index=True)
    transaction_type = models.CharField(
        max_length=32,
        choices=TransactionType.choices,
        db_index=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="JOD")
    provider = models.CharField(max_length=64, blank=True)
    provider_reference = models.CharField(max_length=255, blank=True, db_index=True)
    method = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    raw_response_json = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "payment_transactions"
        indexes = [
            models.Index(fields=["related_entity_type", "related_entity_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_type} {self.amount} {self.status}"

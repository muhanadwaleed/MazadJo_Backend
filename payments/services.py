from django.utils import timezone

from payments.models import PaymentTransaction
from subscriptions.models import AuctionSubscription


def ensure_payment_for_subscription(
    subscription: AuctionSubscription,
) -> PaymentTransaction:
    amount = subscription.subscription_fee
    return PaymentTransaction.objects.create(
        user=subscription.user,
        related_entity_type=PaymentTransaction.RelatedEntityType.SUBSCRIPTION,
        related_entity_id=subscription.id,
        transaction_type=PaymentTransaction.TransactionType.CHARGE,
        amount=amount,
        currency="JOD",
        status=PaymentTransaction.PaymentStatus.PENDING,
    )


def sync_subscription_payment_state(tx: PaymentTransaction) -> None:
    if tx.related_entity_type != PaymentTransaction.RelatedEntityType.SUBSCRIPTION:
        return
    if tx.status not in (
        PaymentTransaction.PaymentStatus.SUCCEEDED,
        PaymentTransaction.PaymentStatus.COMPLETED,
    ):
        return
    try:
        sub = AuctionSubscription.objects.get(pk=tx.related_entity_id)
    except AuctionSubscription.DoesNotExist:
        return
    if sub.status == AuctionSubscription.Status.PENDING_PAYMENT:
        sub.status = AuctionSubscription.Status.ACTIVE
        sub.payment_status = AuctionSubscription.PaymentStatus.PAID
        sub.activated_at = timezone.now()
        sub.save(
            update_fields=["status", "payment_status", "activated_at", "updated_at"]
        )

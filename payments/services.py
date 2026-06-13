from django.utils import timezone

from payments.models import PaymentTransaction
from subscriptions.models import AuctionSubscription
from subscriptions.services import activate_subscription_payment


def ensure_payment_for_subscription(
    subscription: AuctionSubscription,
) -> PaymentTransaction:
    amount = subscription.total_fee
    return PaymentTransaction.objects.create(
        user=subscription.user,
        related_entity_type=PaymentTransaction.RelatedEntityType.SUBSCRIPTION,
        related_entity_id=subscription.id,
        transaction_type=PaymentTransaction.TransactionType.CHARGE,
        amount=amount,
        currency="JOD",
        status=PaymentTransaction.PaymentStatus.PENDING,
    )


def sync_subscription_payment_state(tx: PaymentTransaction, *, request=None) -> None:
    if tx.related_entity_type != PaymentTransaction.RelatedEntityType.SUBSCRIPTION:
        return
    if tx.status not in (
        PaymentTransaction.PaymentStatus.SUCCEEDED,
        PaymentTransaction.PaymentStatus.COMPLETED,
    ):
        return
    try:
        sub = AuctionSubscription.objects.select_related("auction").get(
            pk=tx.related_entity_id
        )
    except AuctionSubscription.DoesNotExist:
        return
    if sub.status == AuctionSubscription.Status.PENDING_PAYMENT:
        paid_at = tx.completed_at or timezone.now()
        activate_subscription_payment(sub, paid_at=paid_at, request=request)

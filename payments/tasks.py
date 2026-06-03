from celery import shared_task
from django.utils import timezone

from payments.models import PaymentTransaction
from payments.services import sync_subscription_payment_state


def _map_payment_status(raw: str) -> str:
    r = (raw or "").lower()
    mapping = {
        "succeeded": PaymentTransaction.PaymentStatus.SUCCEEDED,
        "success": PaymentTransaction.PaymentStatus.SUCCEEDED,
        "completed": PaymentTransaction.PaymentStatus.COMPLETED,
        "failed": PaymentTransaction.PaymentStatus.FAILED,
        "cancelled": PaymentTransaction.PaymentStatus.CANCELLED,
        "pending": PaymentTransaction.PaymentStatus.PENDING,
    }
    return mapping.get(r, PaymentTransaction.PaymentStatus.PROCESSING)


@shared_task
def apply_payment_webhook_payload(payload: dict) -> None:
    ref = (payload.get("provider_reference") or "").strip()
    if not ref:
        return
    tx = PaymentTransaction.objects.filter(provider_reference=ref).first()
    if not tx:
        return
    tx.status = _map_payment_status(str(payload.get("status", "")))
    tx.raw_response_json = payload
    if tx.status in (
        PaymentTransaction.PaymentStatus.SUCCEEDED,
        PaymentTransaction.PaymentStatus.COMPLETED,
    ):
        tx.completed_at = timezone.now()
    tx.save(update_fields=["status", "raw_response_json", "completed_at"])
    sync_subscription_payment_state(tx)

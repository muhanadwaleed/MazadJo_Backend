from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from notifications.models import Notification


@shared_task
def deliver_email_notification(notification_id: int) -> None:
    try:
        n = Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:
        return
    if (
        n.channel != Notification.Channel.EMAIL
        or n.status != Notification.Status.PENDING
    ):
        return
    send_mail(
        subject=n.title,
        message=n.body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[n.user.email] if n.user.email else [],
        fail_silently=True,
    )
    n.status = Notification.Status.SENT
    n.sent_at = timezone.now()
    n.save(update_fields=["status", "sent_at"])


@shared_task
def process_pending_email_notifications(limit: int = 20) -> int:
    ids = list(
        Notification.objects.filter(
            channel=Notification.Channel.EMAIL,
            status=Notification.Status.PENDING,
        ).values_list("id", flat=True)[:limit]
    )
    for nid in ids:
        deliver_email_notification.delay(nid)
    return len(ids)

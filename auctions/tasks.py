from celery import shared_task
from django.db import transaction
from django.utils import timezone

from auctions.models import Auction
from auctions.services import maybe_close_auction


@shared_task
def close_due_auctions() -> int:
    now = timezone.now()
    ids = list(
        Auction.objects.filter(
            status__in=(Auction.Status.ACTIVE, Auction.Status.SCHEDULED),
            ends_at__lt=now,
        ).values_list("pk", flat=True)[:500]
    )
    closed = 0
    for aid in ids:
        with transaction.atomic():
            auction = Auction.objects.select_for_update().get(pk=aid)
            if maybe_close_auction(auction):
                closed += 1
    return closed

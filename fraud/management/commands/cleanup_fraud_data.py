from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import UserFingerprint
from bidding.models import BidIdempotency


class Command(BaseCommand):
    help = (
        "Delete old fingerprint rows and optional old bid idempotency keys "
        "(retention in days; 0 skips that table)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fingerprints-days",
            type=int,
            default=90,
            help="Delete UserFingerprint rows older than this many days (default 90).",
        )
        parser.add_argument(
            "--idempotency-days",
            type=int,
            default=0,
            help="If > 0, delete BidIdempotency rows older than this many days.",
        )

    def handle(self, *args, **options):
        fp_days = int(options["fingerprints_days"])
        idem_days = int(options["idempotency_days"])
        now = timezone.now()

        if fp_days > 0:
            cutoff = now - timedelta(days=fp_days)
            n, _ = UserFingerprint.objects.filter(created_at__lt=cutoff).delete()
            self.stdout.write(
                self.style.NOTICE(f"Deleted {n} fingerprint-related rows.")
            )

        if idem_days > 0:
            cutoff = now - timedelta(days=idem_days)
            n, _ = BidIdempotency.objects.filter(created_at__lt=cutoff).delete()
            self.stdout.write(self.style.NOTICE(f"Deleted {n} idempotency rows."))
        else:
            self.stdout.write("Skipping idempotency cleanup (idempotency-days=0).")

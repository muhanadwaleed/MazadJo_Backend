from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Create default django-celery-beat periodic tasks (idempotent)."

    def handle(self, *args, **options):
        c5, _ = CrontabSchedule.objects.get_or_create(
            minute="*/5",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        otp_iv, _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        sweep_iv, _ = IntervalSchedule.objects.get_or_create(
            every=60,
            period=IntervalSchedule.SECONDS,
        )
        decay_iv, _ = IntervalSchedule.objects.get_or_create(
            every=3600,
            period=IntervalSchedule.SECONDS,
        )
        PeriodicTask.objects.update_or_create(
            name="accounts-cleanup-expired-otps",
            defaults={
                "task": "accounts.tasks.cleanup_expired_otps",
                "interval": otp_iv,
                "crontab": None,
                "enabled": True,
            },
        )
        PeriodicTask.objects.update_or_create(
            name="notifications-pending-email",
            defaults={
                "task": "notifications.tasks.process_pending_email_notifications",
                "crontab": c5,
                "enabled": True,
            },
        )
        PeriodicTask.objects.update_or_create(
            name="auctions-close-due",
            defaults={
                "task": "auctions.tasks.close_due_auctions",
                "interval": sweep_iv,
                "crontab": None,
                "enabled": True,
            },
        )
        PeriodicTask.objects.update_or_create(
            name="fraud-decay-risk-scores",
            defaults={
                "task": "fraud.tasks.decay_risk_scores",
                "interval": decay_iv,
                "crontab": None,
                "enabled": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Periodic tasks OK."))

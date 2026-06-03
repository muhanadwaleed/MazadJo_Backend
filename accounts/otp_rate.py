import logging

from django.conf import settings
from django.utils import timezone

from accounts.models import OtpVerification

otp_logger = logging.getLogger("mazadjo.otp")


def otp_requests_in_window(
    *,
    destination_type: str,
    destination_value: str,
    purpose: str,
) -> int:
    window_min = int(getattr(settings, "OTP_RATE_LIMIT_WINDOW_MINUTES", 10))
    since = timezone.now() - timezone.timedelta(minutes=window_min)
    return OtpVerification.objects.filter(
        destination_type=destination_type,
        destination_value=destination_value,
        purpose=purpose,
        created_at__gte=since,
    ).count()


def assert_otp_rate_allowed(
    *,
    destination_type: str,
    destination_value: str,
    purpose: str,
) -> None:
    from rest_framework.exceptions import Throttled

    max_req = int(getattr(settings, "OTP_RATE_LIMIT_MAX", 3))
    if (
        otp_requests_in_window(
            destination_type=destination_type,
            destination_value=destination_value,
            purpose=purpose,
        )
        >= max_req
    ):
        otp_logger.warning(
            "otp_rate_limited purpose=%s dest_type=%s",
            purpose,
            destination_type,
        )
        raise Throttled(detail="Too many OTP requests. Try again later.")

"""Pre-registration OTP verification (purpose=register)."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from accounts.models import OtpVerification, User


def normalize_destination_value(destination_type: str, destination_value: str) -> str:
    value = (destination_value or "").strip()
    if not value:
        return ""
    if destination_type == OtpVerification.DestinationType.PHONE:
        return "".join(ch for ch in value if ch.isdigit() or ch == "+")
    if destination_type == OtpVerification.DestinationType.EMAIL:
        return value.lower()
    return value


def registration_otp_max_age_minutes() -> int:
    return int(getattr(settings, "REGISTRATION_OTP_MAX_AGE_MINUTES", 30))


def _verified_register_qs(destination_type: str, destination_value: str):
    normalized = normalize_destination_value(destination_type, destination_value)
    if not normalized:
        return OtpVerification.objects.none()
    cutoff = timezone.now() - timedelta(minutes=registration_otp_max_age_minutes())
    return OtpVerification.objects.filter(
        destination_type=destination_type,
        destination_value=normalized,
        purpose=OtpVerification.Purpose.REGISTER,
        verified_at__isnull=False,
        verified_at__gte=cutoff,
        user__isnull=True,
    )


def is_registration_destination_verified(
    destination_type: str, destination_value: str
) -> bool:
    return _verified_register_qs(destination_type, destination_value).exists()


def latest_registration_verification(
    destination_type: str, destination_value: str
) -> OtpVerification | None:
    return (
        _verified_register_qs(destination_type, destination_value)
        .order_by("-verified_at")
        .first()
    )


def consume_registration_verification(
    user: User, destination_type: str, destination_value: str
) -> bool:
    rec = latest_registration_verification(destination_type, destination_value)
    if rec is None:
        return False
    rec.user = user
    rec.save(update_fields=["user"])
    return True


def destination_already_registered(
    destination_type: str, destination_value: str
) -> bool:
    from accounts.utils import find_user_by_otp_destination

    return find_user_by_otp_destination(destination_type, destination_value) is not None

from django.contrib.auth import get_user_model

from accounts.models import OtpVerification
from accounts.verification import normalize_destination_value

User = get_user_model()


def find_user_by_otp_destination(
    destination_type: str, destination_value: str
) -> User | None:
    value = normalize_destination_value(destination_type, destination_value)
    if not value:
        return None
    if destination_type == OtpVerification.DestinationType.PHONE:
        return User.objects.filter(phone_number=value).first()
    if destination_type == OtpVerification.DestinationType.EMAIL:
        return User.objects.filter(email__iexact=value).first()
    return None

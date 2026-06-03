import secrets

from celery import shared_task
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import OtpVerification
from accounts.sms import send_sms


@shared_task
def cleanup_expired_otps() -> int:
    deleted, _ = OtpVerification.objects.filter(expires_at__lt=timezone.now()).delete()
    return deleted


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 1},
)
def dispatch_otp_delivery(self, user_id, destination_type, destination_value, purpose):
    ttl = int(getattr(settings, "OTP_TTL_MINUTES", 10))
    if bool(getattr(settings, "FIXED_OTP", False)):
        plain = "1111"
    else:
        plain = f"{secrets.randbelow(900000) + 100000:06d}"
    expires = timezone.now() + timezone.timedelta(minutes=ttl)
    user = None
    if user_id:
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.filter(pk=user_id).first()
    rec = OtpVerification.objects.create(
        user=user,
        destination_type=destination_type,
        destination_value=destination_value,
        otp_code_hash=make_password(plain),
        purpose=purpose,
        expires_at=expires,
    )
    if destination_type == OtpVerification.DestinationType.EMAIL:
        send_mail(
            subject="Your verification code",
            message=f"Code: {plain}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destination_value],
            fail_silently=True,
        )
    elif destination_type == OtpVerification.DestinationType.PHONE:
        send_sms(destination_value, f"Your code: {plain}")
    return rec.id

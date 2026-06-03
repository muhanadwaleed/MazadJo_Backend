from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class UserType(models.TextChoices):
        PUBLIC_USER = "public_user", "Public User"
        STAFF = "staff", "Staff"
        ADMIN = "admin", "Admin"

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.PUBLIC_USER,
        db_index=True,
    )
    full_name_ar = models.CharField(max_length=255, blank=True)
    full_name_en = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=32, blank=True, db_index=True)
    country_code = models.CharField(max_length=8, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_image = models.CharField(max_length=500, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False, db_index=True)
    is_shadow_banned = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Fraud flag: reject sensitive actions without disclosing policy.",
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.username


class UserRiskScore(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_score",
    )
    score = models.PositiveSmallIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_risk_scores"

    def __str__(self) -> str:
        return f"risk user={self.user_id} score={self.score}"

    def increase(self, amount: int) -> None:
        from django.conf import settings as dj_settings

        cap = int(getattr(dj_settings, "RISK_SCORE_MAX", 100))
        self.score = min(int(self.score) + int(amount), cap)
        self.save(update_fields=["score", "last_updated"])

    def decrease(self, amount: int) -> None:
        self.score = max(int(self.score) - int(amount), 0)
        self.save(update_fields=["score", "last_updated"])

    @property
    def is_shadow_banned(self) -> bool:
        from django.conf import settings as dj_settings

        return self.score >= int(getattr(dj_settings, "RISK_SHADOW_BAN_SCORE", 50))

    @property
    def is_hard_banned(self) -> bool:
        from django.conf import settings as dj_settings

        return self.score >= int(getattr(dj_settings, "RISK_HARD_BAN_SCORE", 80))


class UserFingerprint(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fingerprints",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.TextField(blank=True, null=True)
    device_hash = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_fingerprints"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["device_hash"]),
        ]

    def __str__(self) -> str:
        return f"fingerprint user={self.user_id}"


class UserStats(models.Model):
    """Denormalized counters for fraud heuristics (avoid heavy aggregates per bid)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stats",
    )
    total_bids = models.PositiveIntegerField(default=0)
    total_wins = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_stats"

    def __str__(self) -> str:
        return (
            f"stats user={self.user_id} bids={self.total_bids} wins={self.total_wins}"
        )


class OtpVerification(models.Model):
    class DestinationType(models.TextChoices):
        PHONE = "phone", "Phone"
        EMAIL = "email", "Email"

    class Purpose(models.TextChoices):
        REGISTER = "register", "Register"
        LOGIN_RESET = "login_reset", "Login / Reset"
        VERIFY_PHONE = "verify_phone", "Verify Phone"
        VERIFY_EMAIL = "verify_email", "Verify Email"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="otp_verifications",
    )
    destination_type = models.CharField(max_length=16, choices=DestinationType.choices)
    destination_value = models.CharField(max_length=255)
    otp_code_hash = models.CharField(max_length=255)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    expires_at = models.DateTimeField(db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    resend_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_verifications"
        indexes = [
            models.Index(fields=["destination_type", "destination_value", "purpose"]),
        ]

    def __str__(self) -> str:
        return f"OTP {self.purpose} ({self.destination_type})"

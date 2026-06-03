from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from accounts.models import OtpVerification, User
from accounts.verification import (
    consume_registration_verification,
    is_registration_destination_verified,
    normalize_destination_value,
)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "password",
            "full_name_ar",
            "full_name_en",
            "phone_number",
            "country_code",
        )
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
        }

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        phone = normalize_destination_value(
            OtpVerification.DestinationType.PHONE, attrs.get("phone_number") or ""
        )
        email = normalize_destination_value(
            OtpVerification.DestinationType.EMAIL, attrs.get("email") or ""
        )
        attrs["phone_number"] = phone
        attrs["email"] = email
        errors = {}

        if phone:
            if User.objects.filter(phone_number=phone).exists():
                errors["phone_number"] = "This phone number is already registered."
            elif not is_registration_destination_verified(
                OtpVerification.DestinationType.PHONE, phone
            ):
                errors["phone_number"] = (
                    "Verify this phone number with OTP before registering."
                )

        if email:
            if User.objects.filter(email__iexact=email).exists():
                errors["email"] = "This email is already registered."
            elif not is_registration_destination_verified(
                OtpVerification.DestinationType.EMAIL, email
            ):
                errors["email"] = (
                    "Verify this email with OTP before registering."
                )

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        phone = (validated_data.get("phone_number") or "").strip()
        email = (validated_data.get("email") or "").strip()

        user = User(**validated_data)
        user.set_password(password)

        if phone and is_registration_destination_verified(
            OtpVerification.DestinationType.PHONE, phone
        ):
            user.is_phone_verified = True
        if email and is_registration_destination_verified(
            OtpVerification.DestinationType.EMAIL, email
        ):
            user.is_email_verified = True

        user.save()

        if phone:
            consume_registration_verification(
                user, OtpVerification.DestinationType.PHONE, phone
            )
        if email:
            consume_registration_verification(
                user, OtpVerification.DestinationType.EMAIL, email
            )

        return user


class StaffUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "user_type",
            "is_staff",
            "is_active",
            "full_name_ar",
            "full_name_en",
            "phone_number",
            "country_code",
            "gender",
            "date_of_birth",
            "profile_image",
            "is_phone_verified",
            "is_email_verified",
            "is_blocked",
            "is_shadow_banned",
            "date_joined",
            "updated_at",
        )
        read_only_fields = fields


class StaffUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "full_name_ar",
            "full_name_en",
            "email",
            "phone_number",
            "country_code",
            "gender",
            "date_of_birth",
            "profile_image",
            "user_type",
            "is_staff",
            "is_active",
            "is_blocked",
            "is_shadow_banned",
        )

    def validate_user_type(self, value):
        if value not in User.UserType.values:
            raise serializers.ValidationError("Invalid user type.")
        return value


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "user_type",
            "is_staff",
            "full_name_ar",
            "full_name_en",
            "phone_number",
            "country_code",
            "gender",
            "date_of_birth",
            "profile_image",
            "is_phone_verified",
            "is_email_verified",
            "is_blocked",
            "date_joined",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "username",
            "user_type",
            "is_staff",
            "is_phone_verified",
            "is_email_verified",
            "is_blocked",
            "date_joined",
            "updated_at",
        )


class OtpRequestSerializer(serializers.Serializer):
    destination_type = serializers.ChoiceField(
        choices=OtpVerification.DestinationType.choices
    )
    destination_value = serializers.CharField(max_length=255)
    purpose = serializers.ChoiceField(choices=OtpVerification.Purpose.choices)


class PasswordResetRequestSerializer(serializers.Serializer):
    destination_type = serializers.ChoiceField(
        choices=OtpVerification.DestinationType.choices
    )
    destination_value = serializers.CharField(max_length=255)


class PasswordResetConfirmSerializer(serializers.Serializer):
    destination_type = serializers.ChoiceField(
        choices=OtpVerification.DestinationType.choices
    )
    destination_value = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=8)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class OtpVerificationStatusSerializer(serializers.Serializer):
    destination_type = serializers.ChoiceField(
        choices=OtpVerification.DestinationType.choices
    )
    destination_value = serializers.CharField(max_length=255)
    purpose = serializers.ChoiceField(
        choices=OtpVerification.Purpose.choices,
        default=OtpVerification.Purpose.REGISTER,
    )


class OtpVerifySerializer(serializers.Serializer):
    destination_type = serializers.ChoiceField(
        choices=OtpVerification.DestinationType.choices
    )
    destination_value = serializers.CharField(max_length=255)
    purpose = serializers.ChoiceField(choices=OtpVerification.Purpose.choices)
    code = serializers.CharField(max_length=8)


def apply_verification_flags(user: User, destination_type: str) -> None:
    if destination_type == OtpVerification.DestinationType.EMAIL:
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
    elif destination_type == OtpVerification.DestinationType.PHONE:
        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])


def verify_otp_code(rec: OtpVerification, code: str) -> bool:
    if rec.verified_at or rec.expires_at < timezone.now():
        return False
    return check_password(code, rec.otp_code_hash)

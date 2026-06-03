import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import (
    TokenObtainPairView as SimpleJWTTokenObtainPairView,
)
from rest_framework_simplejwt.views import (
    TokenRefreshView as SimpleJWTTokenRefreshView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OtpVerification
from accounts.otp_rate import assert_otp_rate_allowed
from accounts.serializers import (
    OtpRequestSerializer,
    OtpVerificationStatusSerializer,
    OtpVerifySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserMeSerializer,
    apply_verification_flags,
    verify_otp_code,
)
from accounts.utils import find_user_by_otp_destination
from accounts.verification import (
    destination_already_registered,
    is_registration_destination_verified,
    latest_registration_verification,
    normalize_destination_value,
)
from rest_framework.exceptions import ValidationError
from accounts.exceptions import AccountDisabled, InvalidOtp
from accounts.jwt_serializers import (
    MazadTokenObtainPairSerializer,
    MazadTokenRefreshSerializer,
)
from accounts.tasks import dispatch_otp_delivery
from observability.metrics import record_otp_request, record_otp_verify

User = get_user_model()

otp_logger = logging.getLogger("mazadjo.otp")


class MazadTokenObtainPairView(SimpleJWTTokenObtainPairView):
    serializer_class = MazadTokenObtainPairSerializer


class MazadTokenRefreshView(SimpleJWTTokenRefreshView):
    serializer_class = MazadTokenRefreshSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserMeSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(request=OtpRequestSerializer, responses={200: None})
class OtpRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = OtpRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user if request.user.is_authenticated else None
        if (
            not user
            and ser.validated_data["purpose"] != OtpVerification.Purpose.REGISTER
        ):
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        dest_type = ser.validated_data["destination_type"]
        dest_value = normalize_destination_value(
            dest_type, ser.validated_data["destination_value"]
        )
        purpose = ser.validated_data["purpose"]
        if not dest_value:
            raise ValidationError(
                {"destination_value": "This field may not be blank."}
            )
        if (
            purpose == OtpVerification.Purpose.REGISTER
            and destination_already_registered(dest_type, dest_value)
        ):
            raise ValidationError(
                {
                    "destination_value": (
                        "This phone or email is already registered."
                    )
                }
            )
        assert_otp_rate_allowed(
            destination_type=dest_type,
            destination_value=dest_value,
            purpose=purpose,
        )
        dispatch_otp_delivery.delay(
            user.id if user else None,
            dest_type,
            dest_value,
            purpose,
        )
        record_otp_request()
        otp_logger.info(
            "otp_request purpose=%s dest_type=%s",
            ser.validated_data["purpose"],
            ser.validated_data["destination_type"],
        )
        ttl = int(getattr(settings, "OTP_TTL_MINUTES", 10))
        return Response(
            {
                "detail": "OTP queued for delivery.",
                "expires_in_minutes": ttl,
                "expires_at": timezone.now() + timedelta(minutes=ttl),
            },
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(request=OtpVerifySerializer, responses={200: None})
class OtpVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = OtpVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dest_type = ser.validated_data["destination_type"]
        dest_value = normalize_destination_value(
            dest_type, ser.validated_data["destination_value"]
        )
        purpose = ser.validated_data["purpose"]
        rec = (
            OtpVerification.objects.filter(
                destination_type=dest_type,
                destination_value=dest_value,
                purpose=purpose,
                verified_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if not rec or not verify_otp_code(rec, ser.validated_data["code"]):
            record_otp_verify(success=False)
            otp_logger.info(
                "otp_verify result=fail purpose=%s dest_type=%s",
                ser.validated_data["purpose"],
                ser.validated_data["destination_type"],
            )
            return Response(
                {"detail": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record_otp_verify(success=True)
        otp_logger.info(
            "otp_verify result=ok purpose=%s dest_type=%s",
            ser.validated_data["purpose"],
            ser.validated_data["destination_type"],
        )

        rec.verified_at = timezone.now()
        rec.save(update_fields=["verified_at"])

        if purpose in (
            OtpVerification.Purpose.VERIFY_PHONE,
            OtpVerification.Purpose.VERIFY_EMAIL,
        ):
            user = rec.user or find_user_by_otp_destination(dest_type, dest_value)
            if user is not None:
                apply_verification_flags(user, dest_type)

        payload = {
            "detail": "Verified.",
            "destination_type": dest_type,
            "destination_value": dest_value,
            "purpose": purpose,
        }
        if purpose == OtpVerification.Purpose.REGISTER:
            payload["verified_for_registration"] = True
        return Response(payload)


@extend_schema(request=OtpVerificationStatusSerializer, responses={200: None})
class OtpVerificationStatusView(APIView):
    """Check whether a destination passed register OTP verification (pre-signup)."""

    permission_classes = [AllowAny]

    def post(self, request):
        ser = OtpVerificationStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dest_type = ser.validated_data["destination_type"]
        dest_value = normalize_destination_value(
            dest_type, ser.validated_data["destination_value"]
        )
        purpose = ser.validated_data["purpose"]
        if purpose != OtpVerification.Purpose.REGISTER:
            return Response(
                {"detail": "Only purpose=register is supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        verified = is_registration_destination_verified(dest_type, dest_value)
        rec = latest_registration_verification(dest_type, dest_value)
        return Response(
            {
                "destination_type": dest_type,
                "destination_value": dest_value,
                "verified": verified,
                "verified_at": rec.verified_at if rec else None,
            }
        )


@extend_schema(request=PasswordResetRequestSerializer, responses={202: None})
class PasswordResetRequestView(APIView):
    """Queue OTP for password reset (public; does not reveal whether account exists)."""

    permission_classes = [AllowAny]

    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dest_type = ser.validated_data["destination_type"]
        dest_value = ser.validated_data["destination_value"]
        user = find_user_by_otp_destination(dest_type, dest_value)
        if user is not None:
            if not user.is_active or user.is_blocked:
                raise AccountDisabled()
            assert_otp_rate_allowed(
                destination_type=dest_type,
                destination_value=dest_value,
                purpose=OtpVerification.Purpose.LOGIN_RESET,
            )
            dispatch_otp_delivery.delay(
                user.id,
                dest_type,
                dest_value,
                OtpVerification.Purpose.LOGIN_RESET,
            )
            record_otp_request()
        ttl = int(getattr(settings, "OTP_TTL_MINUTES", 10))
        return Response(
            {
                "detail": "If an account exists for this destination, a reset code was queued.",
                "expires_in_minutes": ttl,
                "expires_at": timezone.now() + timedelta(minutes=ttl),
            },
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(request=PasswordResetConfirmSerializer, responses={200: None})
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rec = (
            OtpVerification.objects.filter(
                destination_type=ser.validated_data["destination_type"],
                destination_value=ser.validated_data["destination_value"],
                purpose=OtpVerification.Purpose.LOGIN_RESET,
                verified_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if not rec or not verify_otp_code(rec, ser.validated_data["code"]):
            record_otp_verify(success=False)
            raise InvalidOtp()
        user = rec.user
        if user is None:
            user = find_user_by_otp_destination(
                rec.destination_type, rec.destination_value
            )
        if user is None or not user.is_active or user.is_blocked:
            raise AccountDisabled()
        rec.verified_at = timezone.now()
        rec.save(update_fields=["verified_at"])
        user.set_password(ser.validated_data["new_password"])
        user.failed_login_attempts = 0
        user.save(update_fields=["password", "failed_login_attempts"])
        record_otp_verify(success=True)
        return Response({"detail": "Password updated."})

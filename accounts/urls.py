from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenVerifyView

from accounts.api import (
    MazadTokenObtainPairView,
    MazadTokenRefreshView,
    MeView,
    OtpRequestView,
    OtpVerificationStatusView,
    OtpVerifyView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)
from accounts.viewsets import StaffUserViewSet

router = DefaultRouter()
router.register(r"users", StaffUserViewSet, basename="staff-user")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="v1-register"),
    path("auth/token/", MazadTokenObtainPairView.as_view(), name="v1-token-obtain"),
    path(
        "auth/token/refresh/",
        MazadTokenRefreshView.as_view(),
        name="v1-token-refresh",
    ),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="v1-token-verify"),
    path("auth/otp/request/", OtpRequestView.as_view(), name="v1-otp-request"),
    path("auth/otp/verify/", OtpVerifyView.as_view(), name="v1-otp-verify"),
    path(
        "auth/otp/verification-status/",
        OtpVerificationStatusView.as_view(),
        name="v1-otp-verification-status",
    ),
    path(
        "auth/password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="v1-password-reset-request",
    ),
    path(
        "auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="v1-password-reset-confirm",
    ),
    path("users/me/", MeView.as_view(), name="v1-users-me"),
    path("", include(router.urls)),
]

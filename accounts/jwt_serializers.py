from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

User = get_user_model()


def _ensure_account_usable(user: User) -> None:
    if not user.is_active or user.is_blocked:
        raise AuthenticationFailed(
            "This account is disabled.",
            code="account_disabled",
        )


class MazadTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        _ensure_account_usable(self.user)
        return data


class MazadTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = self.token_class(attrs["refresh"])
        user = User.objects.filter(pk=refresh["user_id"]).first()
        if user is None:
            raise AuthenticationFailed("User not found.", code="user_not_found")
        _ensure_account_usable(user)
        return data

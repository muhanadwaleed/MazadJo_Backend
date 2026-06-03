from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class ActiveUnblockedJWTAuthentication(JWTAuthentication):
    """Reject JWTs for inactive or blocked accounts on every authenticated request."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_active or user.is_blocked:
            raise AuthenticationFailed(
                "This account is disabled.",
                code="account_disabled",
            )
        return user

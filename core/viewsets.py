from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated

from core.permissions import IsStaffUser


class StaffWritePublicReadMixin:
    """Allow unauthenticated reads; restrict writes to staff."""

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAuthenticated(), IsStaffUser()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.method in SAFE_METHODS and not (
            self.request.user and self.request.user.is_authenticated and self.request.user.is_staff
        ):
            qs = qs.filter(is_active=True)
        return qs

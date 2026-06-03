from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from accounts.serializers import StaffUserSerializer, StaffUserUpdateSerializer
from core.permissions import IsStaffUser

User = get_user_model()


class StaffUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Staff-only user directory for public accounts and staff accounts."""

    permission_classes = [IsAuthenticated, IsStaffUser]
    queryset = User.objects.all().order_by("-date_joined")

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return StaffUserUpdateSerializer
        return StaffUserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        is_staff = params.get("is_staff")
        if is_staff is not None:
            flag = str(is_staff).lower() in ("1", "true", "yes")
            qs = qs.filter(is_staff=flag)

        is_blocked = params.get("is_blocked")
        if is_blocked is not None:
            flag = str(is_blocked).lower() in ("1", "true", "yes")
            qs = qs.filter(is_blocked=flag)

        is_active = params.get("is_active")
        if is_active is not None:
            flag = str(is_active).lower() in ("1", "true", "yes")
            qs = qs.filter(is_active=flag)

        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(full_name_en__icontains=search)
                | Q(full_name_ar__icontains=search)
            )
        return qs

    def perform_update(self, serializer):
        user = self.get_object()
        actor = self.request.user
        if user.pk == actor.pk:
            blocked = serializer.validated_data.get("is_blocked")
            staff = serializer.validated_data.get("is_staff")
            active = serializer.validated_data.get("is_active")
            if blocked is True or staff is False or active is False:
                raise ValidationError(
                    "You cannot block, deactivate, or remove staff access from your own account."
                )
        serializer.save()

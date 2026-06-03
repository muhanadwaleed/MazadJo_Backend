from rest_framework import permissions


class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsOwnerSeller(permissions.BasePermission):
    """Object must be an Auction with seller == request.user."""

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "seller_id", None) == request.user.id

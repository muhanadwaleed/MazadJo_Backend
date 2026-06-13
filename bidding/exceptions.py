from rest_framework.exceptions import PermissionDenied


class SubscriptionRequired(PermissionDenied):
    default_detail = "Active subscription required to bid."
    default_code = "subscription_required"

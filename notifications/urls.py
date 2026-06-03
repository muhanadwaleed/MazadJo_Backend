from django.urls import include, path
from rest_framework.routers import DefaultRouter

from notifications.viewsets import NotificationViewSet

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
]

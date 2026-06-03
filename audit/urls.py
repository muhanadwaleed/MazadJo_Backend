from django.urls import include, path
from rest_framework.routers import DefaultRouter

from audit.viewsets import AuditLogViewSet

router = DefaultRouter()
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", include(router.urls)),
]

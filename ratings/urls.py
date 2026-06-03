from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ratings.viewsets import (
    DisputeViewSet,
    RatingIssueOptionViewSet,
    RatingIssueReportViewSet,
    RatingViewSet,
)

router = DefaultRouter()
router.register(r"ratings/options", RatingIssueOptionViewSet, basename="rating-option")
router.register(r"ratings", RatingViewSet, basename="rating")
router.register(
    r"rating-issue-reports", RatingIssueReportViewSet, basename="rating-issue-report"
)
router.register(r"disputes", DisputeViewSet, basename="dispute")

urlpatterns = [
    path("", include(router.urls)),
]

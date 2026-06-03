from django.db import models
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from ratings.models import Dispute, Rating, RatingIssueOption, RatingIssueReport
from ratings.serializers import (
    DisputeCreateSerializer,
    DisputeSerializer,
    RatingCreateSerializer,
    RatingIssueOptionSerializer,
    RatingIssueReportSerializer,
    RatingSerializer,
)


class RatingIssueOptionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = RatingIssueOption.objects.filter(is_active=True).order_by("code")
    serializer_class = RatingIssueOptionSerializer
    permission_classes = [AllowAny]


class RatingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = Rating.objects.all().select_related("auction", "rater_user", "rated_user")
        if not self.request.user.is_staff:
            qs = qs.filter(
                models.Q(rater_user=self.request.user)
                | models.Q(rated_user=self.request.user)
            )
        auction = self.request.query_params.get("auction")
        if auction:
            qs = qs.filter(auction_id=auction)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return RatingCreateSerializer
        return RatingSerializer


class RatingIssueReportViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = RatingIssueReport.objects.all()
    serializer_class = RatingIssueReportSerializer
    permission_classes = [IsAuthenticated]


class DisputeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = Dispute.objects.all().select_related(
            "auction", "opened_by_user", "against_user"
        )
        if not self.request.user.is_staff:
            qs = qs.filter(
                models.Q(opened_by_user=self.request.user)
                | models.Q(against_user=self.request.user)
            )
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return DisputeCreateSerializer
        return DisputeSerializer

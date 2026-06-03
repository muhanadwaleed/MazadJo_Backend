from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import ProductCategory
from configuration.models import FeesConfiguration, ReviewChecklistItem, TermsAndConditions
from configuration.serializers import (
    FeesConfigurationSerializer,
    ProductCategoryChecklistAssignSerializer,
    ReviewChecklistItemSerializer,
    TermsAndConditionsSerializer,
)
from core.permissions import IsStaffUser
from core.viewsets import StaffWritePublicReadMixin


class FeesConfigurationViewSet(viewsets.ModelViewSet):
    queryset = FeesConfiguration.objects.all().order_by("name")
    serializer_class = FeesConfigurationSerializer

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [AllowAny()]
        return [IsAuthenticated(), IsStaffUser()]


class ReviewChecklistItemViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = ReviewChecklistItem.objects.all()
    serializer_class = ReviewChecklistItemSerializer

    def get_queryset(self):
        qs = ReviewChecklistItem.objects.all().order_by("sort_order", "id")
        if self.request.method in ("GET", "HEAD", "OPTIONS") and not (
            self.request.user
            and self.request.user.is_authenticated
            and self.request.user.is_staff
        ):
            qs = qs.filter(is_active=True)
        return qs


class TermsAndConditionsViewSet(viewsets.ModelViewSet):
    queryset = TermsAndConditions.objects.all().order_by("-effective_at")
    serializer_class = TermsAndConditionsSerializer

    def get_permissions(self):
        if self.action == "active":
            return [AllowAny()]
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [AllowAny()]
        return [IsAuthenticated(), IsStaffUser()]

    def get_queryset(self):
        qs = TermsAndConditions.objects.all().order_by("-effective_at")
        if self.request.method in ("GET", "HEAD", "OPTIONS") and not (
            self.request.user
            and self.request.user.is_authenticated
            and self.request.user.is_staff
        ):
            qs = qs.filter(is_active=True)
        return qs

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        terms = TermsAndConditions.objects.filter(is_active=True).first()
        if terms is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(TermsAndConditionsSerializer(terms).data)


class ProductCategoryChecklistAssignView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser]

    def _assigned_items(self, category):
        links = category.category_checklist_links.select_related(
            "checklist_item"
        ).order_by("sort_order")
        return ReviewChecklistItemSerializer(
            [link.checklist_item for link in links], many=True
        ).data

    def get(self, request, category_id):
        try:
            category = ProductCategory.objects.get(pk=category_id)
        except ProductCategory.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(self._assigned_items(category))

    def put(self, request, category_id):
        try:
            category = ProductCategory.objects.get(pk=category_id)
        except ProductCategory.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = ProductCategoryChecklistAssignSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(category=category)
        return Response(self._assigned_items(category))

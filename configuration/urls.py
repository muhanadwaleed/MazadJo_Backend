from django.urls import include, path
from rest_framework.routers import DefaultRouter

from configuration.viewsets import (
    FeesConfigurationViewSet,
    ProductCategoryChecklistAssignView,
    ReviewChecklistItemViewSet,
    TermsAndConditionsViewSet,
)

router = DefaultRouter()
router.register(
    r"fees-configurations",
    FeesConfigurationViewSet,
    basename="fees-configuration",
)
router.register(
    r"checklist-items",
    ReviewChecklistItemViewSet,
    basename="checklist-item",
)
router.register(r"terms", TermsAndConditionsViewSet, basename="terms")

urlpatterns = [
    path(
        "categories/<int:category_id>/checklist-items/",
        ProductCategoryChecklistAssignView.as_view(),
        name="category-checklist-assign",
    ),
    path("", include(router.urls)),
]

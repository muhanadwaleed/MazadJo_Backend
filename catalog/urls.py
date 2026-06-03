from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalog.viewsets import (
    AreaViewSet,
    CityViewSet,
    CountryViewSet,
    ProductCategoryViewSet,
)

router = DefaultRouter()
router.register(r"countries", CountryViewSet, basename="country")
router.register(r"cities", CityViewSet, basename="city")
router.register(r"areas", AreaViewSet, basename="area")
router.register(r"categories", ProductCategoryViewSet, basename="category")

urlpatterns = [
    path("", include(router.urls)),
]

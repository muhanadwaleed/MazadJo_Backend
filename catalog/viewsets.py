from rest_framework import viewsets

from catalog.models import Area, City, Country, ProductCategory
from catalog.serializers import (
    AreaSerializer,
    CitySerializer,
    CountrySerializer,
    ProductCategorySerializer,
    ProductCategoryWriteSerializer,
)
from core.viewsets import StaffWritePublicReadMixin


class CountryViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    def get_queryset(self):
        return super().get_queryset().order_by("name_en")


class CityViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer

    def get_queryset(self):
        qs = super().get_queryset().order_by("name_en")
        country = self.request.query_params.get("country")
        if country:
            qs = qs.filter(country_id=country)
        return qs


class AreaViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer

    def get_queryset(self):
        qs = super().get_queryset().order_by("name_en")
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city_id=city)
        return qs


class ProductCategoryViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = ProductCategory.objects.select_related(
        "settings", "fees_configuration"
    ).all()
    serializer_class = ProductCategorySerializer

    def get_queryset(self):
        return super().get_queryset().order_by("name_en")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductCategoryWriteSerializer
        return ProductCategorySerializer

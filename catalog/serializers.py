from rest_framework import serializers

from catalog.models import Area, City, Country, ProductCategory, ProductSettings
from configuration.serializers import FeesConfigurationPublicSerializer


class ProductSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSettings
        exclude = ("id", "category")


class ProductSettingsWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSettings
        exclude = ("id", "category")


class ProductCategorySerializer(serializers.ModelSerializer):
    settings = ProductSettingsSerializer(read_only=True)
    fees = FeesConfigurationPublicSerializer(
        source="fees_configuration", read_only=True
    )

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name_ar",
            "name_en",
            "category_type",
            "requires_review",
            "requires_transfer_process",
            "requires_inspection",
            "is_active",
            "settings",
            "fees",
        )


class ProductCategoryWriteSerializer(serializers.ModelSerializer):
    settings = ProductSettingsWriteSerializer(required=False)

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name_ar",
            "name_en",
            "category_type",
            "requires_review",
            "requires_transfer_process",
            "requires_inspection",
            "is_active",
            "fees_configuration",
            "settings",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        settings_data = validated_data.pop("settings", None)
        category = ProductCategory.objects.create(**validated_data)
        if settings_data is not None:
            ProductSettings.objects.create(category=category, **settings_data)
        return category

    def update(self, instance, validated_data):
        settings_data = validated_data.pop("settings", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if settings_data is not None:
            ProductSettings.objects.update_or_create(
                category=instance, defaults=settings_data
            )
        return instance


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("id", "name_ar", "name_en", "code", "is_active")


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "country", "name_ar", "name_en", "is_active")


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ("id", "city", "name_ar", "name_en", "is_active")

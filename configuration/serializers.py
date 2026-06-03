from django.utils import timezone
from rest_framework import serializers

from catalog.models import ProductCategory
from configuration.models import (
    AuctionReviewChecklist,
    FeesConfiguration,
    ProductCategoryChecklist,
    ReviewChecklistItem,
    TermsAndConditions,
)


class FeesConfigurationSerializer(serializers.ModelSerializer):
    category_count = serializers.SerializerMethodField()

    class Meta:
        model = FeesConfiguration
        fields = (
            "id",
            "name",
            "bidder_insurance_amount",
            "seller_insurance_amount",
            "subscription_amount",
            "category_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "category_count")

    def get_category_count(self, obj) -> int:
        return obj.categories.count()

    def validate(self, attrs):
        instance = self.instance
        if instance and not instance.categories.exists():
            pending = attrs.get("name") or instance.name
            if pending:
                pass
        return attrs


class FeesConfigurationPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeesConfiguration
        fields = (
            "bidder_insurance_amount",
            "seller_insurance_amount",
            "subscription_amount",
        )


class ReviewChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewChecklistItem
        fields = (
            "id",
            "key",
            "label_ar",
            "label_en",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProductCategoryChecklistAssignSerializer(serializers.Serializer):
    checklist_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )

    def save(self, category: ProductCategory):
        ids = self.validated_data["checklist_item_ids"]
        items = list(
            ReviewChecklistItem.objects.filter(id__in=ids, is_active=True).order_by(
                "id"
            )
        )
        if len(items) != len(set(ids)):
            raise serializers.ValidationError(
                {"checklist_item_ids": "One or more checklist items are invalid."}
            )
        ProductCategoryChecklist.objects.filter(category=category).delete()
        for sort_order, item in enumerate(items):
            ProductCategoryChecklist.objects.create(
                category=category,
                checklist_item=item,
                sort_order=sort_order,
            )
        return items


class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = (
            "id",
            "version",
            "title_ar",
            "title_en",
            "body_ar",
            "body_en",
            "is_active",
            "effective_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class AuctionReviewChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionReviewChecklist
        fields = (
            "id",
            "checklist_item_key",
            "checklist_item_label",
            "is_checked",
            "checked_by",
            "checked_at",
            "source_item",
        )
        read_only_fields = (
            "id",
            "checklist_item_key",
            "checklist_item_label",
            "source_item",
        )


class AuctionReviewChecklistUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionReviewChecklist
        fields = ("is_checked",)

    def update(self, instance, validated_data):
        is_checked = validated_data.get("is_checked", instance.is_checked)
        request = self.context.get("request")
        if is_checked and request and request.user.is_authenticated:
            instance.is_checked = True
            instance.checked_by = request.user
            instance.checked_at = timezone.now()
        elif not is_checked:
            instance.is_checked = False
            instance.checked_by = None
            instance.checked_at = None
        instance.save(
            update_fields=["is_checked", "checked_by", "checked_at"]
        )
        return instance

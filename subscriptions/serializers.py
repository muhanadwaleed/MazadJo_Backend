import uuid

from django.db import IntegrityError
from rest_framework import serializers

from catalog.models import ProductSettings
from payments.services import ensure_payment_for_subscription
from subscriptions.models import AuctionSubscription


class AuctionSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionSubscription
        fields = (
            "id",
            "auction",
            "user",
            "status",
            "subscription_fee",
            "payment_status",
            "activated_at",
            "withdrawn_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "status",
            "subscription_fee",
            "payment_status",
            "activated_at",
            "withdrawn_at",
            "created_at",
            "updated_at",
        )


class AuctionSubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionSubscription
        fields = ("id", "auction")
        read_only_fields = ("id",)

    def validate_auction(self, auction):
        if not ProductSettings.objects.filter(
            category=auction.product_category
        ).exists():
            raise serializers.ValidationError("Category has no product settings.")
        return auction

    def create(self, validated_data):
        auction = validated_data["auction"]
        fees = auction.product_category.fees_configuration
        request = self.context["request"]
        try:
            sub = AuctionSubscription.objects.create(
                auction=auction,
                user=request.user,
                subscription_fee=fees.subscription_amount,
            )
        except IntegrityError as e:
            raise serializers.ValidationError(
                {"auction": "You already have a subscription for this auction."}
            ) from e
        tx = ensure_payment_for_subscription(sub)
        tx.provider_reference = f"sub-{sub.id}-{uuid.uuid4().hex[:10]}"
        tx.save(update_fields=["provider_reference"])
        return sub

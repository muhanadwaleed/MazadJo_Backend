import uuid

from django.db import IntegrityError
from rest_framework import serializers

from catalog.models import ProductSettings
from payments.models import PaymentTransaction
from payments.serializers import PaymentTransactionSerializer
from payments.services import ensure_payment_for_subscription
from subscriptions.models import AuctionSubscription
from subscriptions.services import (
    compute_subscription_fees,
    participant_type,
    validate_subscribe_eligibility,
)


class AuctionSubscriptionSerializer(serializers.ModelSerializer):
    participant_type = serializers.SerializerMethodField()
    payment_transaction = serializers.SerializerMethodField()

    class Meta:
        model = AuctionSubscription
        fields = (
            "id",
            "auction",
            "user",
            "status",
            "insurance_fee",
            "subscription_fee",
            "total_fee",
            "participant_type",
            "payment_status",
            "payment_transaction",
            "activated_at",
            "withdrawn_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_participant_type(self, obj) -> str:
        return participant_type(obj.auction, obj.user)

    def get_payment_transaction(self, obj):
        tx = (
            PaymentTransaction.objects.filter(
                related_entity_type=PaymentTransaction.RelatedEntityType.SUBSCRIPTION,
                related_entity_id=obj.id,
            )
            .order_by("-initiated_at")
            .first()
        )
        if tx is None:
            return None
        return PaymentTransactionSerializer(tx).data


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
        request = self.context["request"]
        validate_subscribe_eligibility(auction, request.user)
        return auction

    def create(self, validated_data):
        auction = validated_data["auction"]
        request = self.context["request"]
        idem = request.headers.get("Idempotency-Key") or request.headers.get(
            "X-Idempotency-Key"
        )
        idem_clean = (idem or "").strip()[:128]

        if idem_clean:
            existing = AuctionSubscription.objects.filter(
                auction=auction, user=request.user, idempotency_key=idem_clean
            ).first()
            if existing:
                return existing

        existing_sub = AuctionSubscription.objects.filter(
            auction=auction, user=request.user
        ).first()
        if existing_sub:
            if existing_sub.status == AuctionSubscription.Status.PENDING_PAYMENT:
                return existing_sub
            raise serializers.ValidationError(
                {"auction": "You already have a subscription for this auction."}
            )

        insurance, subscription, total = compute_subscription_fees(auction, request.user)
        try:
            sub = AuctionSubscription.objects.create(
                auction=auction,
                user=request.user,
                insurance_fee=insurance,
                subscription_fee=subscription,
                total_fee=total,
                idempotency_key=idem_clean,
            )
        except IntegrityError as e:
            raise serializers.ValidationError(
                {"auction": "You already have a subscription for this auction."}
            ) from e
        tx = ensure_payment_for_subscription(sub)
        tx.provider_reference = f"sub-{sub.id}-{uuid.uuid4().hex[:10]}"
        tx.save(update_fields=["provider_reference"])
        return sub

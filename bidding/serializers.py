from rest_framework import serializers

from bidding.models import Bid
from bidding.utils import mask_username


class BidPublicSerializer(serializers.ModelSerializer):
    bidder = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Bid
        fields = ("id", "amount", "bidder", "timestamp")

    def get_bidder(self, obj):
        if not obj.bidder_id:
            return "***"
        return mask_username(obj.bidder.username)


class BidSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = (
            "id",
            "auction",
            "bidder",
            "amount",
            "increment_amount",
            "bid_source",
            "status",
            "rejection_reason",
            "created_at",
        )
        read_only_fields = fields


class BidPlaceSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    bid_source = serializers.ChoiceField(
        choices=Bid.BidSource.choices, default=Bid.BidSource.MANUAL
    )

from rest_framework import serializers

from auctions.media_urls import auction_media_serve_url
from auctions.models import Auction, AuctionMedia, AuctionWatchlist
from auctions.validation import default_min_bid_increment, validate_auction_fields
from catalog.models import ProductSettings


class AuctionMediaSerializer(serializers.ModelSerializer):
    """Media metadata for list/detail — never exposes raw ``file_data``."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = AuctionMedia
        fields = (
            "id",
            "media_type",
            "file_type",
            "file_name",
            "is_blurred",
            "sort_order",
            "url",
        )

    def get_url(self, obj: AuctionMedia) -> str:
        request = self.context.get("request")
        return auction_media_serve_url(obj.auction_id, obj.id, request)


class AuctionWriteSerializer(serializers.ModelSerializer):
    """Create/update draft auctions (seller-owned, editable only in draft states)."""

    class Meta:
        model = Auction
        fields = (
            "id",
            "status",
            "auction_number",
            "current_price",
            "created_at",
            "updated_at",
            "product_category",
            "title",
            "description",
            "area",
            "location_link",
            "start_price",
            "reserve_price",
            "min_bid_increment",
            "starts_at",
            "ends_at",
            "is_anonymous_bidding",
        )
        read_only_fields = (
            "id",
            "status",
            "auction_number",
            "current_price",
            "created_at",
            "updated_at",
        )

    def validate_product_category(self, category):
        if not ProductSettings.objects.filter(category=category).exists():
            raise serializers.ValidationError("Category has no product settings.")
        return category

    def validate(self, attrs):
        inst = self.instance
        if inst is not None and inst.status not in (
            Auction.Status.DRAFT,
            Auction.Status.RETURNED_FOR_EDIT,
        ):
            raise serializers.ValidationError(
                {"status": "Auction cannot be edited in this state."}
            )

        category = attrs.get("product_category") or (
            inst.product_category if inst else None
        )
        if inst is None and "min_bid_increment" not in attrs and category is not None:
            attrs["min_bid_increment"] = default_min_bid_increment(category)

        if category is not None:
            probe = inst if inst is not None else Auction()
            probe.product_category = category
            probe.start_price = attrs.get(
                "start_price", getattr(inst, "start_price", None)
            )
            probe.reserve_price = attrs.get(
                "reserve_price", getattr(inst, "reserve_price", None)
            )
            probe.location_link = attrs.get(
                "location_link", getattr(inst, "location_link", "")
            )
            validate_auction_fields(probe, require_media=False)

        return attrs

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if "start_price" in validated_data:
            instance.current_price = validated_data["start_price"]
            instance.save(update_fields=["current_price", "updated_at"])
        return instance


class AuctionListSerializer(serializers.ModelSerializer):
    primary_media_url = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = (
            "id",
            "auction_number",
            "title",
            "status",
            "start_price",
            "current_price",
            "min_bid_increment",
            "starts_at",
            "ends_at",
            "participants_count",
            "views_count",
            "product_category",
            "seller",
            "primary_media_url",
        )

    def get_primary_media_url(self, obj: Auction):
        media = (
            obj.media_items.filter(media_type=AuctionMedia.MediaType.IMAGE)
            .order_by("sort_order", "id")
            .first()
        )
        if media is None:
            return None
        request = self.context.get("request")
        return auction_media_serve_url(obj.id, media.id, request)


class AuctionDetailSerializer(serializers.ModelSerializer):
    media_items = AuctionMediaSerializer(many=True, read_only=True)
    is_on_watchlist = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = (
            "id",
            "auction_number",
            "title",
            "description",
            "status",
            "start_price",
            "current_price",
            "reserve_price",
            "min_bid_increment",
            "starts_at",
            "ends_at",
            "origin_deadline",
            "extend_deadline",
            "actual_end_at",
            "extension_count",
            "area",
            "location_link",
            "participants_count",
            "views_count",
            "is_anonymous_bidding",
            "product_category",
            "seller",
            "winner_user",
            "winner_bid",
            "created_at",
            "updated_at",
            "media_items",
            "is_on_watchlist",
        )

    def get_is_on_watchlist(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if not user or not user.is_authenticated:
            return False
        return AuctionWatchlist.objects.filter(auction=obj, user=user).exists()


class AuctionWatchlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionWatchlist
        fields = ("id", "auction", "user", "created_at")
        read_only_fields = ("id", "user", "created_at")


class AuctionWatchlistEntrySerializer(serializers.ModelSerializer):
    """Watchlist row for the authenticated user (`GET /watchlist/`)."""

    auction = AuctionListSerializer(read_only=True)

    class Meta:
        model = AuctionWatchlist
        fields = ("id", "created_at", "auction")
        read_only_fields = ("id", "created_at", "auction")

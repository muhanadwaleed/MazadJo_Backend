import uuid

from django.conf import settings
from django.db.models import F, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from auctions.models import Auction, AuctionMedia, AuctionReviewLog, AuctionWatchlist
from auctions.visibility import (
    can_edit_auction_media,
    can_serve_auction_media,
    filter_auctions_for_request,
)
from auctions.serializers import (
    AuctionDetailSerializer,
    AuctionListSerializer,
    AuctionMediaSerializer,
    AuctionWatchlistEntrySerializer,
    AuctionWatchlistSerializer,
    AuctionWriteSerializer,
)
from auctions.services import (
    maybe_close_auction,
    on_auction_entered_review,
    perform_seller_cancel,
    perform_staff_publish,
    perform_staff_review,
)
from auctions.validation import validate_auction_fields, validate_media_upload
from configuration.models import AuctionReviewChecklist
from configuration.serializers import (
    AuctionReviewChecklistSerializer,
    AuctionReviewChecklistUpdateSerializer,
)
from bidding.models import Bid
from bidding.pagination import BidCursorPagination
from bidding.serializers import BidPlaceSerializer, BidPublicSerializer, BidSerializer
from bidding.services import place_bid
from core.permissions import IsOwnerSeller, IsStaffUser


class AuctionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "pk"

    def get_permissions(self):
        if self.action in ("staff_review", "staff_publish", "review_checklist"):
            return [IsAuthenticated(), IsStaffUser()]
        if self.action in (
            "update",
            "partial_update",
            "submit",
            "media_upload",
            "cancel",
        ):
            return [IsAuthenticated(), IsOwnerSeller()]
        if self.action == "media_detail" and self.request.method == "DELETE":
            return [IsAuthenticated(), IsOwnerSeller()]
        if self.action == "list":
            mine = self.request.query_params.get("mine", "").strip().lower()
            if mine in ("1", "true", "yes"):
                return [IsAuthenticated()]
        if self.action in ("list", "retrieve", "bids", "media_detail") and (
            self.request.method == "GET"
        ):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = (
            Auction.objects.all()
            .select_related("seller", "product_category")
            .prefetch_related("media_items")
            .order_by("-starts_at")
        )
        qs = filter_auctions_for_request(
            qs,
            user=self.request.user,
            action=self.action,
            status=self.request.query_params.get("status"),
            mine=self.request.query_params.get("mine"),
        )
        cat = self.request.query_params.get("category")
        if cat:
            qs = qs.filter(product_category_id=cat)
        area = self.request.query_params.get("area")
        if area:
            qs = qs.filter(area_id=area)
        q = self.request.query_params.get("search")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        seller_id = self.request.query_params.get("seller")
        if (
            seller_id
            and self.request.user.is_authenticated
            and self.request.user.is_staff
        ):
            qs = qs.filter(seller_id=seller_id)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AuctionDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return AuctionWriteSerializer
        return AuctionListSerializer

    def perform_create(self, serializer):
        serializer.save(
            seller=self.request.user,
            status=Auction.Status.DRAFT,
            auction_number=uuid.uuid4().hex[:12].upper(),
            current_price=serializer.validated_data["start_price"],
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        maybe_close_auction(instance)
        Auction.objects.filter(pk=instance.pk).update(
            views_count=F("views_count") + 1
        )
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"], url_path="watchlist")
    def watchlist(self, request, pk=None):
        auction = self.get_object()
        if request.method == "POST":
            obj, created = AuctionWatchlist.objects.get_or_create(
                auction=auction, user=request.user
            )
            ser = AuctionWatchlistSerializer(obj)
            return Response(
                ser.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        deleted, _ = AuctionWatchlist.objects.filter(
            auction=auction, user=request.user
        ).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="bids")
    def bids(self, request, pk=None):
        auction = self.get_object()
        if request.method == "GET":
            qs = (
                Bid.objects.filter(auction=auction, suppress_publication=False)
                .select_related("bidder")
                .order_by("-created_at", "-id")
            )
            since = request.query_params.get("since")
            if since:
                dt = parse_datetime(since)
                if dt is not None:
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone.get_current_timezone())
                    qs = qs.filter(created_at__gt=dt)
            paginator = BidCursorPagination()
            page = paginator.paginate_queryset(qs, request)
            if page is not None:
                return paginator.get_paginated_response(
                    BidPublicSerializer(page, many=True).data
                )
            return Response(BidPublicSerializer(qs, many=True).data)
        ser = BidPlaceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        idem = request.headers.get("Idempotency-Key") or request.headers.get(
            "X-Idempotency-Key"
        )
        idem_clean = idem.strip() if idem else ""
        bid = place_bid(
            auction_id=auction.id,
            user_id=request.user.id,
            amount=ser.validated_data["amount"],
            bid_source=ser.validated_data["bid_source"],
            idempotency_key=idem_clean or None,
        )
        return Response(BidSerializer(bid).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        auction = self.get_object()
        if auction.status not in (
            Auction.Status.DRAFT,
            Auction.Status.RETURNED_FOR_EDIT,
        ):
            return Response(
                {"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST
            )
        validate_auction_fields(auction, require_media=True)
        auction.status = Auction.Status.UNDER_REVIEW
        auction.save(update_fields=["status", "updated_at"])
        on_auction_entered_review(auction)
        return Response(
            AuctionDetailSerializer(auction, context={"request": request}).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="media",
        parser_classes=[MultiPartParser, FormParser],
    )
    def media_upload(self, request, pk=None):
        auction = self.get_object()
        if not can_edit_auction_media(auction, request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response(
                {"detail": "Field 'file' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        media_type = request.data.get("media_type", AuctionMedia.MediaType.IMAGE)
        if media_type not in AuctionMedia.MediaType.values:
            return Response(
                {"detail": "Invalid media_type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sort_order_raw = request.data.get("sort_order", 0)
        try:
            sort_order = int(sort_order_raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid sort_order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_blurred = str(request.data.get("is_blurred", "false")).lower() in (
            "1",
            "true",
            "yes",
        )
        max_bytes = getattr(
            settings, "AUCTION_MEDIA_MAX_BYTES", 10 * 1024 * 1024
        )
        validate_media_upload(
            auction,
            media_type=media_type,
            file_name=uploaded.name,
            file_size=uploaded.size,
            is_blurred=is_blurred,
            max_bytes=max_bytes,
        )

        file_data = uploaded.read()
        media = AuctionMedia.objects.create(
            auction=auction,
            media_type=media_type,
            file_data=file_data,
            file_type=uploaded.content_type or "application/octet-stream",
            file_name=uploaded.name,
            is_blurred=is_blurred,
            sort_order=sort_order,
        )
        return Response(
            AuctionMediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get", "delete"],
        url_path=r"media/(?P<media_id>[^/.]+)",
    )
    def media_detail(self, request, pk=None, media_id=None):
        auction = self.get_object()

        if request.method == "DELETE":
            if not can_edit_auction_media(auction, request.user):
                return Response(status=status.HTTP_403_FORBIDDEN)
            try:
                media = AuctionMedia.objects.get(pk=media_id, auction=auction)
            except AuctionMedia.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            media.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if not can_serve_auction_media(auction, request.user):
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            media = AuctionMedia.objects.get(pk=media_id, auction=auction)
        except AuctionMedia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(
            bytes(media.file_data),
            content_type=media.file_type or "application/octet-stream",
        )
        if media.file_name:
            response["Content-Disposition"] = (
                f'inline; filename="{media.file_name}"'
            )
        return response

    @action(detail=True, methods=["get", "patch"], url_path="review-checklist")
    def review_checklist(self, request, pk=None):
        auction = self.get_object()
        if request.method == "GET":
            if auction.status == Auction.Status.UNDER_REVIEW:
                on_auction_entered_review(auction)
            items = AuctionReviewChecklist.objects.filter(auction=auction).order_by(
                "id"
            )
            return Response(AuctionReviewChecklistSerializer(items, many=True).data)
        item_id = request.data.get("id")
        if not item_id:
            return Response(
                {"detail": "Field 'id' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            item = AuctionReviewChecklist.objects.get(pk=item_id, auction=auction)
        except AuctionReviewChecklist.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = AuctionReviewChecklistUpdateSerializer(
            item, data=request.data, partial=True, context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(AuctionReviewChecklistSerializer(item).data)

    @action(detail=True, methods=["post"], url_path="staff/review")
    def staff_review(self, request, pk=None):
        auction = self.get_object()
        decision = request.data.get("decision")
        reason = request.data.get("reason", "")
        if decision not in AuctionReviewLog.Decision.values:
            return Response(
                {"detail": "Invalid decision."}, status=status.HTTP_400_BAD_REQUEST
            )
        auction = perform_staff_review(
            auction,
            reviewer=request.user,
            decision=decision,
            reason=reason,
            request=request,
        )
        return Response(
            AuctionDetailSerializer(auction, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="staff/publish")
    def staff_publish(self, request, pk=None):
        auction = self.get_object()
        auction = perform_staff_publish(
            auction, publisher=request.user, request=request
        )
        return Response(
            AuctionDetailSerializer(auction, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        auction = self.get_object()
        reason = request.data.get("reason", "")
        auction = perform_seller_cancel(
            auction,
            seller=request.user,
            reason=reason,
            request=request,
        )
        return Response(
            AuctionDetailSerializer(auction, context={"request": request}).data
        )


class WatchlistViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Lists auction watchlist rows for the **authenticated user only**.

    No query parameters accept another user's id; rows are always scoped to
    ``request.user``.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AuctionWatchlistEntrySerializer

    def get_queryset(self):
        return (
            AuctionWatchlist.objects.filter(user=self.request.user)
            .select_related(
                "auction",
                "auction__seller",
                "auction__product_category",
            )
            .order_by("-created_at")
        )

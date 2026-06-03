from datetime import timedelta
from decimal import Decimal
import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from auctions.models import Auction
from bidding.models import Bid
from bidding.services import place_bid
from catalog.models import ProductSettings
from catalog.tests.helpers import create_test_category
from subscriptions.models import AuctionSubscription

User = get_user_model()


class PlaceBidAntiSnipingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.seller = User.objects.create_user(username="s", password="p1")
        self.bidder = User.objects.create_user(username="b", password="p2")
        self.cat = create_test_category(name_ar="x", name_en="Cat")
        ProductSettings.objects.create(
            category=self.cat,
            auction_extension_enabled=True,
            extension_minutes=3,
            extension_trigger_seconds=120,
        )
        now = timezone.now()
        self.auction = Auction.objects.create(
            seller=self.seller,
            product_category=self.cat,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="t",
            status=Auction.Status.ACTIVE,
            start_price=Decimal("100"),
            current_price=Decimal("100"),
            min_bid_increment=Decimal("10"),
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(seconds=60),
            origin_deadline=now + timedelta(seconds=60),
            extend_deadline=now + timedelta(seconds=60),
        )
        AuctionSubscription.objects.create(
            auction=self.auction,
            user=self.bidder,
            subscription_fee=Decimal("1"),
            status=AuctionSubscription.Status.ACTIVE,
            payment_status=AuctionSubscription.PaymentStatus.PAID,
        )

    def test_extends_end_when_inside_snipe_window(self):
        ends_before = self.auction.ends_at
        place_bid(
            auction_id=self.auction.id,
            user_id=self.bidder.id,
            amount=Decimal("110"),
            bid_source=Bid.BidSource.MANUAL,
        )
        self.auction.refresh_from_db()
        self.assertGreater(self.auction.ends_at, ends_before)
        self.assertEqual(self.auction.extension_count, 1)
        self.assertEqual(self.auction.extend_deadline, self.auction.ends_at)

    def test_no_extension_outside_window(self):
        self.auction.ends_at = timezone.now() + timedelta(minutes=10)
        self.auction.extension_count = 0
        self.auction.save()
        ends_before = self.auction.ends_at
        place_bid(
            auction_id=self.auction.id,
            user_id=self.bidder.id,
            amount=Decimal("110"),
            bid_source=Bid.BidSource.MANUAL,
        )
        self.auction.refresh_from_db()
        self.assertEqual(self.auction.ends_at, ends_before)
        self.assertEqual(self.auction.extension_count, 0)

    def test_force_extension_last_seconds_even_if_trigger_large(self):
        ps = ProductSettings.objects.get(category=self.cat)
        ps.extension_trigger_seconds = 300
        ps.save()
        now = timezone.now()
        self.auction.ends_at = now + timedelta(seconds=5)
        self.auction.extension_count = 0
        self.auction.save()
        ends_before = self.auction.ends_at
        place_bid(
            auction_id=self.auction.id,
            user_id=self.bidder.id,
            amount=Decimal("110"),
            bid_source=Bid.BidSource.MANUAL,
        )
        self.auction.refresh_from_db()
        self.assertGreater(self.auction.ends_at, ends_before)

    def test_idempotency_returns_same_bid(self):
        b1 = place_bid(
            auction_id=self.auction.id,
            user_id=self.bidder.id,
            amount=Decimal("110"),
            bid_source=Bid.BidSource.MANUAL,
            idempotency_key="client-retry-xyz",
        )
        b2 = place_bid(
            auction_id=self.auction.id,
            user_id=self.bidder.id,
            amount=Decimal("999.00"),
            bid_source=Bid.BidSource.MANUAL,
            idempotency_key="client-retry-xyz",
        )
        self.assertEqual(b1.id, b2.id)
        self.assertEqual(b1.amount, Decimal("110"))

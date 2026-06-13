import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from auctions.models import Auction
from catalog.models import ProductSettings
from catalog.tests.helpers import create_test_category
from subscriptions.models import AuctionSubscription

User = get_user_model()


class SubscriptionFeeFromConfigurationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.seller = User.objects.create_user(username="s", password="p")
        self.bidder = User.objects.create_user(username="b", password="p")
        self.category = create_test_category(
            name_en="Cat",
            name_ar="ف",
            fees_name="Subscription fee test",
            subscription_amount=Decimal("7.50"),
            bidder_insurance=Decimal("2.00"),
            seller_insurance=Decimal("1.00"),
        )
        ProductSettings.objects.create(category=self.category)
        now = timezone.now()
        self.auction = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="A",
            status=Auction.Status.ACTIVE,
            start_price=Decimal("10"),
            current_price=Decimal("10"),
            min_bid_increment=Decimal("1"),
            duration_days=7,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
        )
        self.client.force_authenticate(self.bidder)

    def test_bidder_subscription_uses_insurance_plus_subscription(self):
        response = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        sub = AuctionSubscription.objects.get(pk=response.data["id"])
        self.assertEqual(sub.subscription_fee, Decimal("7.50"))
        self.assertEqual(sub.insurance_fee, Decimal("2.00"))
        self.assertEqual(sub.total_fee, Decimal("9.50"))

    def test_idempotency_key_scoped_to_auction(self):
        now = timezone.now()
        other_auction = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="B",
            status=Auction.Status.ACTIVE,
            start_price=Decimal("10"),
            current_price=Decimal("10"),
            min_bid_increment=Decimal("1"),
            duration_days=7,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
        )
        idem_key = "shared-client-key"
        first = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
            HTTP_IDEMPOTENCY_KEY=idem_key,
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": other_auction.id},
            format="json",
            HTTP_IDEMPOTENCY_KEY=idem_key,
        )
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(second.data["id"], first.data["id"])
        self.assertEqual(second.data["auction"], other_auction.id)

        replay = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": other_auction.id},
            format="json",
            HTTP_IDEMPOTENCY_KEY=idem_key,
        )
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(replay.data["id"], second.data["id"])

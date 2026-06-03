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
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
        )
        self.client.force_authenticate(self.bidder)

    def test_subscription_uses_fees_configuration_amount(self):
        response = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        sub = AuctionSubscription.objects.get(pk=response.data["id"])
        self.assertEqual(sub.subscription_fee, Decimal("7.50"))

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
import uuid

from auctions.models import Auction, AuctionWatchlist
from catalog.models import ProductSettings
from catalog.tests.helpers import create_test_category

User = get_user_model()


class WatchlistListMineOnlyTests(TestCase):
    def setUp(self):
        self.category = create_test_category(name_ar="C", name_en="Cat")
        ProductSettings.objects.create(category=self.category)
        self.alice = User.objects.create_user(username="alice", password="alice-pass-99")
        self.bob = User.objects.create_user(username="bob", password="bob-pass-99")

        def make_auction(title: str, seller: User) -> Auction:
            now = timezone.now()
            return Auction.objects.create(
                seller=seller,
                product_category=self.category,
                auction_number=uuid.uuid4().hex[:12].upper(),
                title=title,
                status=Auction.Status.ACTIVE,
                start_price="10.00",
                current_price="10.00",
                min_bid_increment="1.00",
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(days=1),
                origin_deadline=now + timedelta(days=1),
                extend_deadline=now + timedelta(days=1),
            )

        self.auction_a = make_auction("For Alice", self.alice)
        self.auction_b = make_auction("For Bob", self.bob)

        AuctionWatchlist.objects.create(auction=self.auction_a, user=self.alice)
        AuctionWatchlist.objects.create(auction=self.auction_b, user=self.bob)

        self.client = APIClient()

    def test_list_returns_only_own_entries(self):
        self.client.force_authenticate(self.alice)
        url = reverse("watchlist-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        titles = {row["auction"]["title"] for row in results}
        self.assertEqual(titles, {"For Alice"})
        self.assertEqual(len(results), 1)

    def test_unauthenticated_cannot_list(self):
        url = reverse("watchlist-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

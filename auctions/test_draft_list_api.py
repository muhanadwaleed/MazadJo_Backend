"""API tests for draft auction create/update and list filters (mine, seller)."""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from auctions.models import Auction
from catalog.models import Area, City, Country, ProductSettings
from catalog.tests.helpers import create_test_category

User = get_user_model()


class AuctionDraftApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.country = Country.objects.create(name_ar="J", name_en="Jordan", code="JO")
        self.city = City.objects.create(
            country=self.country, name_ar="A", name_en="Amman"
        )
        self.area = Area.objects.create(city=self.city, name_ar="X", name_en="Downtown")
        self.category = create_test_category(name_ar="C", name_en="Cars")
        ProductSettings.objects.create(category=self.category)
        self.seller = User.objects.create_user(
            username="seller1", password="seller-pass-99"
        )
        self.other = User.objects.create_user(
            username="seller2", password="other-pass-99"
        )
        self.staff = User.objects.create_user(
            username="staff1", password="staff-pass-99", is_staff=True
        )
        self.now = timezone.now()

    def _draft_payload(self, title="My car"):
        return {
            "product_category": self.category.id,
            "title": title,
            "description": "Nice",
            "area": self.area.id,
            "start_price": "1000.00",
            "min_bid_increment": "50.00",
            "starts_at": (self.now + timedelta(days=1)).isoformat(),
            "ends_at": (self.now + timedelta(days=2)).isoformat(),
        }

    def test_create_draft_requires_auth(self):
        url = reverse("auction-list")
        r = self.client.post(url, self._draft_payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_draft_success(self):
        self.client.force_authenticate(self.seller)
        url = reverse("auction-list")
        r = self.client.post(url, self._draft_payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["status"], Auction.Status.DRAFT)
        self.assertEqual(Decimal(r.data["start_price"]), Decimal("1000.00"))
        self.assertEqual(Decimal(r.data["current_price"]), Decimal("1000.00"))
        self.assertTrue(r.data["auction_number"])
        aid = r.data["id"]
        a = Auction.objects.get(pk=aid)
        self.assertEqual(a.seller_id, self.seller.id)
        self.assertEqual(a.status, Auction.Status.DRAFT)

    def test_patch_draft_owner_updates_start_price_syncs_current(self):
        self.client.force_authenticate(self.seller)
        a = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="T",
            status=Auction.Status.DRAFT,
            start_price=Decimal("100"),
            current_price=Decimal("100"),
            min_bid_increment=Decimal("10"),
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
        )
        url = reverse("auction-detail", args=[a.id])
        r = self.client.patch(
            url, {"start_price": "200.00"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        a.refresh_from_db()
        self.assertEqual(a.start_price, Decimal("200.00"))
        self.assertEqual(a.current_price, Decimal("200.00"))

    def test_patch_draft_forbidden_for_non_owner(self):
        self.client.force_authenticate(self.other)
        a = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="T",
            status=Auction.Status.DRAFT,
            start_price=Decimal("100"),
            current_price=Decimal("100"),
            min_bid_increment=Decimal("10"),
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
        )
        url = reverse("auction-detail", args=[a.id])
        r = self.client.patch(url, {"title": "Hacked"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_mine_requires_auth(self):
        url = reverse("auction-list")
        r = self.client.get(url, {"mine": "1"})
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_mine_returns_only_own_auctions(self):
        Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="Mine",
            status=Auction.Status.DRAFT,
            start_price=Decimal("10"),
            current_price=Decimal("10"),
            min_bid_increment=Decimal("1"),
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
        )
        Auction.objects.create(
            seller=self.other,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="Theirs",
            status=Auction.Status.DRAFT,
            start_price=Decimal("20"),
            current_price=Decimal("20"),
            min_bid_increment=Decimal("1"),
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
        )
        self.client.force_authenticate(self.seller)
        url = reverse("auction-list")
        r = self.client.get(url, {"mine": "1"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        titles = {row["title"] for row in r.data["results"]}
        self.assertEqual(titles, {"Mine"})

    def test_list_seller_filter_applies_only_for_staff(self):
        Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="A1",
            status=Auction.Status.DRAFT,
            start_price=Decimal("10"),
            current_price=Decimal("10"),
            min_bid_increment=Decimal("1"),
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
        )
        Auction.objects.create(
            seller=self.other,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="A2",
            status=Auction.Status.DRAFT,
            start_price=Decimal("20"),
            current_price=Decimal("20"),
            min_bid_increment=Decimal("1"),
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
        )
        url = reverse("auction-list")
        self.client.force_authenticate(self.other)
        r = self.client.get(url, {"seller": str(self.seller.id)})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        titles = {row["title"] for row in r.data["results"]}
        self.assertEqual(titles, set())
        self.client.force_authenticate(self.staff)
        r2 = self.client.get(url, {"seller": str(self.seller.id)})
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        titles2 = {row["title"] for row in r2.data["results"]}
        self.assertEqual(titles2, {"A1"})

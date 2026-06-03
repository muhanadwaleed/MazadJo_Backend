"""Tests for auction list visibility by status (public vs staff)."""

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


class AuctionStatusVisibilityTests(TestCase):
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
        self.staff = User.objects.create_user(
            username="staff1", password="staff-pass-99", is_staff=True
        )
        self.now = timezone.now()
        self.list_url = reverse("auction-list")

    def _create(self, *, title, auction_status, seller=None):
        return Auction.objects.create(
            seller=seller or self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title=title,
            status=auction_status,
            start_price=Decimal("100"),
            current_price=Decimal("100"),
            min_bid_increment=Decimal("10"),
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
        )

    def test_anon_cannot_list_under_review_status(self):
        self._create(title="Hidden", auction_status=Auction.Status.UNDER_REVIEW)
        self._create(title="Live", auction_status=Auction.Status.ACTIVE)

        r = self.client.get(self.list_url, {"status": "under_review"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["results"], [])

    def test_anon_list_default_excludes_drafts(self):
        self._create(title="Draft", auction_status=Auction.Status.DRAFT)
        self._create(title="Live", auction_status=Auction.Status.ACTIVE)

        r = self.client.get(self.list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        titles = {row["title"] for row in r.data["results"]}
        self.assertEqual(titles, {"Live"})

    def test_staff_can_list_under_review(self):
        self._create(title="Queue", auction_status=Auction.Status.UNDER_REVIEW)
        self.client.force_authenticate(self.staff)

        r = self.client.get(self.list_url, {"status": "under_review"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        titles = {row["title"] for row in r.data["results"]}
        self.assertEqual(titles, {"Queue"})

    def test_seller_mine_includes_own_draft(self):
        self._create(title="My draft", auction_status=Auction.Status.DRAFT)
        self.client.force_authenticate(self.seller)

        r = self.client.get(self.list_url, {"mine": "1"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        titles = {row["title"] for row in r.data["results"]}
        self.assertEqual(titles, {"My draft"})

    def test_anon_cannot_retrieve_draft_detail(self):
        auction = self._create(title="Secret", auction_status=Auction.Status.DRAFT)
        url = reverse("auction-detail", args=[auction.id])

        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_retrieve_own_draft(self):
        auction = self._create(title="My draft", auction_status=Auction.Status.DRAFT)
        url = reverse("auction-detail", args=[auction.id])
        self.client.force_authenticate(self.seller)

        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["title"], "My draft")

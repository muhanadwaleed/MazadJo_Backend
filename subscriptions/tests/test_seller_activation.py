"""Phase 5: seller/bidder fees, seller payment activates auction."""

import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from auctions.models import Auction, AuctionMedia
from catalog.models import ProductSettings
from catalog.tests.helpers import create_test_category
from configuration.models import ProductCategoryChecklist, ReviewChecklistItem
from payments.models import PaymentTransaction
from subscriptions.models import AuctionSubscription

User = get_user_model()

TINY_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"


class SellerActivationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = create_test_category(
            name_en="Cars",
            name_ar="سيارات",
            subscription_amount=Decimal("5.00"),
            seller_insurance=Decimal("10.00"),
            bidder_insurance=Decimal("2.00"),
        )
        ProductSettings.objects.create(
            category=self.category, min_images_count=1, max_images_count=5
        )
        checklist_item = ReviewChecklistItem.objects.create(
            key="ok", label_en="OK", label_ar="موافق"
        )
        ProductCategoryChecklist.objects.create(
            category=self.category,
            checklist_item=checklist_item,
        )
        self.seller = User.objects.create_user(username="seller", password="p")
        self.bidder = User.objects.create_user(username="bidder", password="p")
        self.now = timezone.now()
        self.auction = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="Car",
            status=Auction.Status.APPROVED,
            start_price=Decimal("100"),
            current_price=Decimal("100"),
            min_bid_increment=Decimal("10"),
            duration_days=5,
        )
        AuctionMedia.objects.create(
            auction=self.auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="a.png",
        )

    def test_seller_subscribe_charges_insurance_plus_subscription(self):
        self.client.force_authenticate(self.seller)
        r = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["participant_type"], "seller")
        self.assertEqual(Decimal(r.data["insurance_fee"]), Decimal("10.00"))
        self.assertEqual(Decimal(r.data["subscription_fee"]), Decimal("5.00"))
        self.assertEqual(Decimal(r.data["total_fee"]), Decimal("15.00"))
        self.assertEqual(
            Decimal(r.data["payment_transaction"]["amount"]), Decimal("15.00")
        )

    def test_seller_mark_paid_activates_auction(self):
        self.client.force_authenticate(self.seller)
        create = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        sub_id = create.data["id"]
        r = self.client.post(reverse("subscription-mark-paid", args=[sub_id]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.auction.refresh_from_db()
        self.assertEqual(self.auction.status, Auction.Status.ACTIVE)
        self.assertIsNotNone(self.auction.starts_at)
        self.assertIsNotNone(self.auction.ends_at)
        self.assertEqual(
            self.auction.ends_at.date(),
            (self.auction.starts_at + timedelta(days=5)).date(),
        )

    @patch("subscriptions.services.activate_subscription_payment")
    def test_mark_paid_rolls_back_payment_on_activation_failure(self, mock_activate):
        mock_activate.side_effect = RuntimeError("activation failed")
        self.client.force_authenticate(self.seller)
        create = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        sub_id = create.data["id"]
        tx = PaymentTransaction.objects.get(
            related_entity_type=PaymentTransaction.RelatedEntityType.SUBSCRIPTION,
            related_entity_id=sub_id,
        )
        self.client.raise_request_exception = False
        response = self.client.post(reverse("subscription-mark-paid", args=[sub_id]))
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        sub = AuctionSubscription.objects.get(pk=sub_id)
        tx.refresh_from_db()
        self.auction.refresh_from_db()
        self.assertEqual(sub.status, AuctionSubscription.Status.PENDING_PAYMENT)
        self.assertEqual(tx.status, PaymentTransaction.PaymentStatus.PENDING)
        self.assertIsNone(tx.completed_at)
        self.assertEqual(self.auction.status, Auction.Status.APPROVED)

    def test_bidder_cannot_subscribe_before_active(self):
        self.client.force_authenticate(self.bidder)
        r = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bidder_subscribe_after_seller_activation(self):
        self.client.force_authenticate(self.seller)
        create = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        self.client.post(reverse("subscription-mark-paid", args=[create.data["id"]]))
        self.auction.refresh_from_db()
        self.client.force_authenticate(self.bidder)
        r = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["participant_type"], "bidder")
        self.assertEqual(Decimal(r.data["total_fee"]), Decimal("7.00"))

    def test_place_bid_without_subscription_returns_403(self):
        self.client.force_authenticate(self.seller)
        create = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        self.client.post(reverse("subscription-mark-paid", args=[create.data["id"]]))
        self.client.force_authenticate(self.bidder)
        r = self.client.post(
            reverse("auction-bids", args=[self.auction.id]),
            {"amount": "110.00"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(r.data["error"]["code"], "subscription_required")

    def test_cannot_mark_other_users_subscription_paid(self):
        self.client.force_authenticate(self.seller)
        create = self.client.post(
            "/api/v1/subscriptions/",
            {"auction": self.auction.id},
            format="json",
        )
        sub_id = create.data["id"]
        self.client.force_authenticate(self.bidder)
        r = self.client.post(reverse("subscription-mark-paid", args=[sub_id]))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

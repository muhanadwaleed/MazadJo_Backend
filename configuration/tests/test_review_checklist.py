import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from auctions.models import Auction
from catalog.tests.helpers import create_test_category
from configuration.models import ProductCategoryChecklist, ReviewChecklistItem
from configuration.services.review_checklist import ensure_auction_review_checklist

User = get_user_model()


class ReviewChecklistSnapshotTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username="s", password="p")
        self.category = create_test_category(name_en="C", name_ar="ف")
        self.item = ReviewChecklistItem.objects.create(
            key="title_ok",
            label_en="Title OK",
            label_ar="عنوان",
        )
        ProductCategoryChecklist.objects.create(
            category=self.category,
            checklist_item=self.item,
            sort_order=0,
        )
        now = timezone.now()
        self.auction = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="Test",
            status=Auction.Status.UNDER_REVIEW,
            start_price=Decimal("10"),
            current_price=Decimal("10"),
            min_bid_increment=Decimal("1"),
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
        )

    def test_ensure_checklist_is_idempotent(self):
        created = ensure_auction_review_checklist(self.auction)
        self.assertEqual(created, 1)
        self.assertEqual(self.auction.review_checklist_items.count(), 1)
        created_again = ensure_auction_review_checklist(self.auction)
        self.assertEqual(created_again, 0)
        self.assertEqual(self.auction.review_checklist_items.count(), 1)


class ReviewChecklistValidationTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username="s", password="p")
        self.category = create_test_category(name_en="C", name_ar="ف")
        self.item = ReviewChecklistItem.objects.create(
            key="title_ok",
            label_en="Title OK",
            label_ar="عنوان",
        )
        ProductCategoryChecklist.objects.create(
            category=self.category,
            checklist_item=self.item,
            sort_order=0,
        )
        now = timezone.now()
        self.auction = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="Test",
            status=Auction.Status.UNDER_REVIEW,
            start_price=Decimal("10"),
            current_price=Decimal("10"),
            min_bid_increment=Decimal("1"),
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
        )
        ensure_auction_review_checklist(self.auction)

    def test_validate_raises_when_unchecked(self):
        from configuration.services.review_checklist import (
            validate_review_checklist_complete,
        )
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            validate_review_checklist_complete(self.auction)

    def test_validate_passes_when_all_checked(self):
        from configuration.services.review_checklist import (
            validate_review_checklist_complete,
        )

        self.auction.review_checklist_items.update(is_checked=True)
        validate_review_checklist_complete(self.auction)

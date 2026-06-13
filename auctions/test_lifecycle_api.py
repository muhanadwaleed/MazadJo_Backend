"""API tests for auction lifecycle: review, publish, seller cancel, audit."""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from auctions.models import Auction, AuctionMedia
from audit.models import AuditLog
from catalog.models import Area, City, Country, ProductSettings
from catalog.tests.helpers import create_test_category
from configuration.models import ProductCategoryChecklist, ReviewChecklistItem
User = get_user_model()

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


class AuctionLifecycleApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.country = Country.objects.create(name_ar="J", name_en="Jordan", code="JO")
        self.city = City.objects.create(
            country=self.country, name_ar="A", name_en="Amman"
        )
        self.area = Area.objects.create(city=self.city, name_ar="X", name_en="Downtown")
        self.category = create_test_category(name_ar="C", name_en="Cars")
        ProductSettings.objects.create(
            category=self.category,
            min_images_count=1,
            max_images_count=5,
        )
        self.checklist_item = ReviewChecklistItem.objects.create(
            key="title_ok",
            label_en="Title OK",
            label_ar="عنوان",
        )
        ProductCategoryChecklist.objects.create(
            category=self.category,
            checklist_item=self.checklist_item,
            sort_order=0,
        )
        self.seller = User.objects.create_user(
            username="seller1", password="seller-pass-99"
        )
        self.staff = User.objects.create_user(
            username="staff1", password="staff-pass-99", is_staff=True
        )
        self.now = timezone.now()

    def _create_draft(self, *, title="My car", seller=None):
        return Auction.objects.create(
            seller=seller or self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title=title,
            description="Nice",
            status=Auction.Status.DRAFT,
            start_price=Decimal("1000"),
            current_price=Decimal("1000"),
            min_bid_increment=Decimal("50"),
            duration_days=7,
        )

    def _add_image(self, auction):
        AuctionMedia.objects.create(
            auction=auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="photo.png",
        )

    def _submit(self, auction):
        self.client.force_authenticate(self.seller)
        return self.client.post(reverse("auction-submit", args=[auction.id]))

    def test_submit_snapshots_checklist(self):
        auction = self._create_draft()
        self._add_image(auction)
        r = self._submit(auction)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], Auction.Status.UNDER_REVIEW)
        self.assertEqual(auction.review_checklist_items.count(), 1)

    def test_approve_fails_when_checklist_incomplete(self):
        auction = self._create_draft()
        self._add_image(auction)
        self._submit(auction)
        self.client.force_authenticate(self.staff)
        r = self.client.post(
            reverse("auction-staff-review", args=[auction.id]),
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        auction.refresh_from_db()
        self.assertEqual(auction.status, Auction.Status.UNDER_REVIEW)

    def test_approve_succeeds_when_checklist_complete(self):
        auction = self._create_draft()
        self._add_image(auction)
        self._submit(auction)
        row = auction.review_checklist_items.get()
        self.client.force_authenticate(self.staff)
        self.client.patch(
            reverse("auction-review-checklist", args=[auction.id]),
            {"id": row.id, "is_checked": True},
            format="json",
        )
        r = self.client.post(
            reverse("auction-staff-review", args=[auction.id]),
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], Auction.Status.APPROVED)
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="auction",
                entity_id=auction.id,
                action="staff_review_approve",
            ).exists()
        )

    def test_approve_without_checklist_items_succeeds(self):
        ProductCategoryChecklist.objects.filter(category=self.category).delete()
        auction = self._create_draft()
        self._add_image(auction)
        self._submit(auction)
        self.client.force_authenticate(self.staff)
        r = self.client.post(
            reverse("auction-staff-review", args=[auction.id]),
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], Auction.Status.APPROVED)

    def test_seller_cancel_draft(self):
        auction = self._create_draft()
        self.client.force_authenticate(self.seller)
        r = self.client.post(
            reverse("auction-cancel", args=[auction.id]),
            {"reason": "changed mind"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], Auction.Status.CANCELLED)
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="auction",
                entity_id=auction.id,
                action="seller_cancel",
            ).exists()
        )

    def test_seller_cancel_scheduled(self):
        auction = self._create_draft()
        auction.status = Auction.Status.SCHEDULED
        auction.save(update_fields=["status"])
        self.client.force_authenticate(self.seller)
        r = self.client.post(reverse("auction-cancel", args=[auction.id]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], Auction.Status.CANCELLED)

    def test_staff_cannot_cancel(self):
        auction = self._create_draft()
        self.client.force_authenticate(self.staff)
        r = self.client.post(reverse("auction-cancel", args=[auction.id]))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_cannot_cancel_active(self):
        auction = self._create_draft()
        auction.status = Auction.Status.ACTIVE
        auction.save(update_fields=["status"])
        self.client.force_authenticate(self.seller)
        r = self.client.post(reverse("auction-cancel", args=[auction.id]))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_return_for_edit_does_not_require_checklist(self):
        auction = self._create_draft()
        self._add_image(auction)
        self._submit(auction)
        self.client.force_authenticate(self.staff)
        r = self.client.post(
            reverse("auction-staff-review", args=[auction.id]),
            {"decision": "return_for_edit", "reason": "fix photos"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], Auction.Status.RETURNED_FOR_EDIT)

    def test_reject_does_not_require_checklist(self):
        auction = self._create_draft()
        self._add_image(auction)
        self._submit(auction)
        self.client.force_authenticate(self.staff)
        r = self.client.post(
            reverse("auction-staff-review", args=[auction.id]),
            {"decision": "reject", "reason": "policy"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], Auction.Status.REJECTED)

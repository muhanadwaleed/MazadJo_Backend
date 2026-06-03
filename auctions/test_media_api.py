"""API tests for auction media upload/serve/delete and ProductSettings validation."""

import io
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
from catalog.models import Area, City, Country, ProductSettings
from catalog.tests.helpers import create_test_category

User = get_user_model()

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


class AuctionMediaApiTests(TestCase):
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
            min_images_count=2,
            max_images_count=5,
            allowed_extensions_json=[".png", ".jpg"],
        )
        self.seller = User.objects.create_user(
            username="seller1", password="seller-pass-99"
        )
        self.other = User.objects.create_user(
            username="seller2", password="other-pass-99"
        )
        self.now = timezone.now()
        self.auction = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="My car",
            description="Rare vintage",
            status=Auction.Status.DRAFT,
            start_price=Decimal("1000"),
            current_price=Decimal("1000"),
            min_bid_increment=Decimal("50"),
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
        )

    def _upload_url(self, auction_id=None):
        return reverse("auction-media-upload", args=[auction_id or self.auction.id])

    def _media_url(self, media_id, auction_id=None):
        return reverse(
            "auction-media-detail",
            args=[auction_id or self.auction.id, media_id],
        )

    def _upload(self, user=None, **extra):
        self.client.force_authenticate(user or self.seller)
        data = {
            "file": io.BytesIO(TINY_PNG),
            "media_type": "image",
            "sort_order": "0",
        }
        data.update(extra)
        data["file"].name = extra.get("file_name", "photo.png")
        return self.client.post(self._upload_url(), data, format="multipart")

    def test_upload_media_success(self):
        r = self._upload()
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("file_data", r.data)
        self.assertIn("url", r.data)
        self.assertTrue(r.data["url"].endswith(f"/media/{r.data['id']}/"))

    def test_upload_forbidden_for_non_owner(self):
        self.client.force_authenticate(self.other)
        r = self.client.post(
            self._upload_url(),
            {"file": io.BytesIO(TINY_PNG), "media_type": "image"},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_forbidden_when_not_draft(self):
        self.auction.status = Auction.Status.UNDER_REVIEW
        self.auction.save(update_fields=["status"])
        r = self._upload()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_serve_media_owner_on_draft(self):
        media = AuctionMedia.objects.create(
            auction=self.auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="photo.png",
        )
        self.client.force_authenticate(self.seller)
        r = self.client.get(self._media_url(media.id))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertEqual(r.content, TINY_PNG)

    def test_serve_media_anon_blocked_on_draft(self):
        media = AuctionMedia.objects.create(
            auction=self.auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="photo.png",
        )
        r = self.client.get(self._media_url(media.id))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_serve_media_public_when_scheduled(self):
        self.auction.status = Auction.Status.SCHEDULED
        self.auction.save(update_fields=["status"])
        media = AuctionMedia.objects.create(
            auction=self.auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="photo.png",
        )
        r = self.client.get(self._media_url(media.id))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_delete_media_owner(self):
        media = AuctionMedia.objects.create(
            auction=self.auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="photo.png",
        )
        self.client.force_authenticate(self.seller)
        r = self.client.delete(self._media_url(media.id))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AuctionMedia.objects.filter(pk=media.id).exists())

    def test_detail_excludes_file_data(self):
        AuctionMedia.objects.create(
            auction=self.auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="photo.png",
        )
        self.client.force_authenticate(self.seller)
        url = reverse("auction-detail", args=[self.auction.id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["media_items"]), 1)
        self.assertNotIn("file_data", r.data["media_items"][0])
        self.assertIn("url", r.data["media_items"][0])

    def test_list_primary_media_url(self):
        media = AuctionMedia.objects.create(
            auction=self.auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="photo.png",
            sort_order=0,
        )
        self.auction.status = Auction.Status.ACTIVE
        self.auction.save(update_fields=["status"])
        r = self.client.get(reverse("auction-list"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        row = r.data["results"][0]
        self.assertIn("primary_media_url", row)
        self.assertTrue(row["primary_media_url"].endswith(f"/media/{media.id}/"))

    def test_submit_fails_without_min_images(self):
        AuctionMedia.objects.create(
            auction=self.auction,
            media_type=AuctionMedia.MediaType.IMAGE,
            file_data=TINY_PNG,
            file_type="image/png",
            file_name="photo.png",
        )
        self.client.force_authenticate(self.seller)
        url = reverse("auction-submit", args=[self.auction.id])
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_succeeds_with_min_images(self):
        for i in range(2):
            AuctionMedia.objects.create(
                auction=self.auction,
                media_type=AuctionMedia.MediaType.IMAGE,
                file_data=TINY_PNG,
                file_type="image/png",
                file_name=f"photo{i}.png",
                sort_order=i,
            )
        self.client.force_authenticate(self.seller)
        url = reverse("auction-submit", args=[self.auction.id])
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], Auction.Status.UNDER_REVIEW)

    def test_search_matches_description(self):
        self.auction.status = Auction.Status.ACTIVE
        self.auction.save(update_fields=["status"])
        r = self.client.get(reverse("auction-list"), {"search": "vintage"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 1)

    def test_area_filter(self):
        self.auction.area = self.area
        self.auction.status = Auction.Status.ACTIVE
        self.auction.save(update_fields=["area", "status"])
        r = self.client.get(reverse("auction-list"), {"area": str(self.area.id)})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 1)

    def test_views_count_increments_on_retrieve(self):
        self.auction.status = Auction.Status.ACTIVE
        self.auction.save(update_fields=["status"])
        url = reverse("auction-detail", args=[self.auction.id])
        r1 = self.client.get(url)
        r2 = self.client.get(url)
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.auction.refresh_from_db()
        self.assertEqual(self.auction.views_count, 2)

    def test_upload_rejects_bad_extension(self):
        data = {
            "file": io.BytesIO(b"not-a-real-image"),
            "media_type": "image",
        }
        data["file"].name = "photo.gif"
        self.client.force_authenticate(self.seller)
        r = self.client.post(self._upload_url(), data, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from auctions.models import Auction
from catalog.models import Area, City, Country, ProductSettings
from catalog.tests.helpers import create_test_category
from payments.models import PaymentTransaction

User = get_user_model()


@override_settings(WEBHOOK_PAYMENT_SECRET="test-secret", CELERY_TASK_ALWAYS_EAGER=True)
class ApiV1FlowTests(TestCase):
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
            username="seller", password="seller-pass-99"
        )
        self.bidder = User.objects.create_user(
            username="bidder", password="bidder-pass-99"
        )
        self.staff = User.objects.create_user(
            username="staff", password="staff-pass-99", is_staff=True
        )

    def _verify_register_otp(self, destination_type, destination_value):
        self.client.post(
            reverse("v1-otp-request"),
            {
                "destination_type": destination_type,
                "destination_value": destination_value,
                "purpose": "register",
            },
            format="json",
        )
        self.client.post(
            reverse("v1-otp-verify"),
            {
                "destination_type": destination_type,
                "destination_value": destination_value,
                "purpose": "register",
                "code": "1111",
            },
            format="json",
        )

    @override_settings(FIXED_OTP=True, CELERY_TASK_ALWAYS_EAGER=True)
    def test_register_token_me(self):
        email = "u1@example.com"
        self._verify_register_otp("email", email)
        r = self.client.post(
            reverse("v1-register"),
            {
                "username": "u1",
                "password": "complex-pass-99",
                "email": email,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        tok = self.client.post(
            reverse("v1-token-obtain"),
            {"username": "u1", "password": "complex-pass-99"},
            format="json",
        )
        self.assertEqual(tok.status_code, status.HTTP_200_OK)
        access = tok.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = self.client.get(reverse("v1-users-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["username"], "u1")

    def test_auction_flow_publish_subscribe_bid_webhook(self):
        self.client.force_authenticate(self.seller)
        now = timezone.now()
        auction = Auction.objects.create(
            seller=self.seller,
            product_category=self.category,
            auction_number=uuid.uuid4().hex[:12].upper(),
            title="Car",
            description="Nice",
            area=self.area,
            start_price=Decimal("1000.00"),
            current_price=Decimal("1000.00"),
            min_bid_increment=Decimal("50.00"),
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            origin_deadline=now + timedelta(days=2),
            extend_deadline=now + timedelta(days=2),
            status=Auction.Status.DRAFT,
        )
        aid = auction.id
        submit = self.client.post(reverse("auction-submit", args=[aid]))
        self.assertEqual(submit.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(self.staff)
        review = self.client.post(
            reverse("auction-staff-review", args=[aid]),
            {"decision": "approve", "reason": ""},
            format="json",
        )
        self.assertEqual(review.status_code, status.HTTP_200_OK)
        pub = self.client.post(reverse("auction-staff-publish", args=[aid]))
        self.assertEqual(pub.status_code, status.HTTP_200_OK)
        auction = Auction.objects.get(pk=aid)
        now = timezone.now()
        auction.starts_at = now - timedelta(hours=1)
        auction.ends_at = now + timedelta(hours=2)
        auction.status = Auction.Status.ACTIVE
        auction.save(update_fields=["starts_at", "ends_at", "status"])

        self.client.force_authenticate(self.bidder)
        sub = self.client.post(
            reverse("subscription-list"), {"auction": aid}, format="json"
        )
        self.assertEqual(sub.status_code, status.HTTP_201_CREATED)
        sid = sub.data["id"]
        self.client.force_authenticate(self.staff)
        mp = self.client.post(reverse("subscription-mark-paid", args=[sid]))
        self.assertEqual(mp.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.bidder)
        bid = self.client.post(
            reverse("auction-bids", args=[aid]),
            {"amount": "1100.00", "bid_source": "manual"},
            format="json",
        )
        self.assertEqual(bid.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(bid.data["amount"]), Decimal("1100.00"))

        tx = PaymentTransaction.objects.filter(
            related_entity_type=PaymentTransaction.RelatedEntityType.SUBSCRIPTION,
            related_entity_id=sid,
        ).first()
        self.assertIsNotNone(tx)
        body = json.dumps(
            {"provider_reference": tx.provider_reference, "status": "succeeded"}
        )
        sig = (
            "sha256="
            + hmac.new(b"test-secret", body.encode(), hashlib.sha256).hexdigest()
        )
        self.client.credentials()
        wh = self.client.post(
            reverse("payment-webhook"),
            body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )
        self.assertEqual(wh.status_code, status.HTTP_202_ACCEPTED)
        tx.refresh_from_db()
        self.assertEqual(tx.status, PaymentTransaction.PaymentStatus.SUCCEEDED)

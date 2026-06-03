from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalog.tests.helpers import create_test_category
from configuration.models import (
    FeesConfiguration,
    ReviewChecklistItem,
    TermsAndConditions,
)

User = get_user_model()


class ConfigurationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.fees = FeesConfiguration.objects.create(
            name="Standard",
            bidder_insurance_amount=Decimal("1"),
            seller_insurance_amount=Decimal("2"),
            subscription_amount=Decimal("5"),
        )
        self.category = create_test_category(
            name_en="Cat",
            name_ar="فئة",
            fees_name="Standard",
        )

    def test_public_categories_include_fees(self):
        response = self.client.get("/api/v1/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        row = next(r for r in results if r["name_en"] == "Cat")
        self.assertEqual(row["fees"]["subscription_amount"], "5.00")

    def test_terms_active_endpoint(self):
        TermsAndConditions.objects.create(
            version="v1",
            title_en="T",
            title_ar="ع",
            body_en="Body",
            body_ar="نص",
            is_active=True,
            effective_at=timezone.now(),
        )
        response = self.client.get("/api/v1/terms/active/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], "v1")

    def test_staff_assigns_category_checklist(self):
        item = ReviewChecklistItem.objects.create(
            key="photos",
            label_en="Photos OK",
            label_ar="صور",
        )
        self.client.force_authenticate(self.staff)
        response = self.client.put(
            f"/api/v1/categories/{self.category.id}/checklist-items/",
            {"checklist_item_ids": [item.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_staff_gets_category_checklist(self):
        item = ReviewChecklistItem.objects.create(
            key="title",
            label_en="Title OK",
            label_ar="عنوان",
        )
        self.client.force_authenticate(self.staff)
        self.client.put(
            f"/api/v1/categories/{self.category.id}/checklist-items/",
            {"checklist_item_ids": [item.id]},
            format="json",
        )
        response = self.client.get(
            f"/api/v1/categories/{self.category.id}/checklist-items/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["key"], "title")

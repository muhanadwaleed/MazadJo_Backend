from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import Area, City, Country, ProductCategory, ProductSettings
from catalog.tests.helpers import create_test_category
from configuration.models import FeesConfiguration

User = get_user_model()


class CatalogApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user", password="pass")
        self.fees = FeesConfiguration.objects.create(
            name="Standard",
            bidder_insurance_amount=Decimal("1"),
            seller_insurance_amount=Decimal("2"),
            subscription_amount=Decimal("5"),
        )
        self.active_country = Country.objects.create(
            name_en="Jordan",
            name_ar="الأردن",
            code="JO",
            is_active=True,
        )
        Country.objects.create(
            name_en="Hidden",
            name_ar="مخفي",
            code="XX",
            is_active=False,
        )
        self.active_category = create_test_category(
            name_en="Active Cat",
            name_ar="نشط",
            fees_name="Standard",
            is_active=True,
        )
        self.inactive_category = create_test_category(
            name_en="Hidden Cat",
            name_ar="مخفي",
            fees_name="Standard",
            is_active=False,
        )
        ProductSettings.objects.create(category=self.active_category)

    def test_public_countries_lists_active_only(self):
        response = self.client.get("/api/v1/countries/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["code"], "JO")

    def test_staff_sees_inactive_countries(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/v1/countries/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        codes = {row["code"] for row in results}
        self.assertIn("JO", codes)
        self.assertIn("XX", codes)

    def test_staff_can_create_country(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/countries/",
            {
                "name_en": "UAE",
                "name_ar": "الإمارات",
                "code": "AE",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Country.objects.filter(code="AE").exists())

    def test_non_staff_cannot_create_country(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/countries/",
            {
                "name_en": "Nope",
                "name_ar": "لا",
                "code": "NP",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_categories_lists_active_only(self):
        response = self.client.get("/api/v1/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        names = {row["name_en"] for row in results}
        self.assertIn("Active Cat", names)
        self.assertNotIn("Hidden Cat", names)

    def test_staff_can_create_category_with_settings(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/categories/",
            {
                "name_en": "New Cat",
                "name_ar": "جديد",
                "category_type": "general",
                "requires_review": True,
                "requires_transfer_process": False,
                "requires_inspection": False,
                "is_active": True,
                "fees_configuration": self.fees.id,
                "settings": {
                    "min_images_count": 2,
                    "max_images_count": 8,
                    "video_allowed": False,
                    "min_start_price": "10.00",
                    "min_bid_increment": "5.00",
                    "delivery_period_days": 7,
                    "is_active": True,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        category = ProductCategory.objects.get(name_en="New Cat")
        self.assertTrue(hasattr(category, "settings"))
        self.assertEqual(category.settings.min_images_count, 2)

    def test_staff_can_update_category_settings(self):
        ProductSettings.objects.create(category=self.inactive_category)
        self.client.force_authenticate(self.staff)
        response = self.client.patch(
            f"/api/v1/categories/{self.inactive_category.id}/",
            {"settings": {"min_images_count": 5, "max_images_count": 15}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.inactive_category.settings.refresh_from_db()
        self.assertEqual(self.inactive_category.settings.min_images_count, 5)

    def test_staff_can_create_city(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/cities/",
            {
                "country": self.active_country.id,
                "name_en": "Amman",
                "name_ar": "عمان",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            City.objects.filter(name_en="Amman", country=self.active_country).exists()
        )

    def test_staff_can_create_area(self):
        city = City.objects.create(
            country=self.active_country,
            name_en="Amman",
            name_ar="عمان",
            is_active=True,
        )
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/areas/",
            {
                "city": city.id,
                "name_en": "Abdoun",
                "name_ar": "عبدون",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Area.objects.filter(name_en="Abdoun", city=city).exists())

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Area, City, Country, ProductCategory, ProductSettings


class SeedCatalogCommandTests(TestCase):
    def test_seed_catalog_is_idempotent(self):
        call_command("seed_catalog")
        countries = Country.objects.count()
        cities = City.objects.count()
        areas = Area.objects.count()
        categories = ProductCategory.objects.count()
        settings = ProductSettings.objects.count()

        call_command("seed_catalog")

        self.assertEqual(Country.objects.count(), countries)
        self.assertEqual(City.objects.count(), cities)
        self.assertEqual(Area.objects.count(), areas)
        self.assertEqual(ProductCategory.objects.count(), categories)
        self.assertEqual(ProductSettings.objects.count(), settings)

    def test_seed_catalog_jordan_and_categories(self):
        call_command("seed_catalog")
        jordan = Country.objects.get(code="JO")
        self.assertEqual(jordan.name_en, "Jordan")
        self.assertTrue(
            City.objects.filter(country=jordan, name_en="Amman").exists()
        )
        amman = City.objects.get(country=jordan, name_en="Amman")
        self.assertTrue(Area.objects.filter(city=amman, name_en="Abdoun").exists())
        electronics = ProductCategory.objects.get(name_en="Electronics")
        self.assertTrue(
            ProductSettings.objects.filter(category=electronics).exists()
        )
        ps = electronics.settings
        self.assertTrue(ps.video_allowed)
        self.assertEqual(electronics.fees_configuration.subscription_amount, 5)


class CatalogApiTests(TestCase):
    def setUp(self):
        call_command("seed_catalog")
        self.client = APIClient()

    def test_categories_nested_settings(self):
        response = self.client.get("/api/v1/categories/")
        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", response.data)
        self.assertGreaterEqual(len(results), 4)
        electronics = next(
            r for r in results if r["name_en"] == "Electronics"
        )
        self.assertIn("settings", electronics)
        self.assertEqual(electronics["fees"]["subscription_amount"], "5.00")
        self.assertTrue(electronics["settings"]["video_allowed"])

    def test_geo_filters(self):
        country_id = Country.objects.get(code="JO").id
        amman_id = City.objects.get(name_en="Amman").id

        cities = self.client.get(
            f"/api/v1/cities/?country={country_id}"
        ).data
        city_results = cities.get("results", cities)
        self.assertTrue(any(c["name_en"] == "Amman" for c in city_results))

        areas = self.client.get(f"/api/v1/areas/?city={amman_id}").data
        area_results = areas.get("results", areas)
        self.assertTrue(any(a["name_en"] == "Abdoun" for a in area_results))

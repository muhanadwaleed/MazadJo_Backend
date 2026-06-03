"""Seed Jordan geo hierarchy and sample product categories with settings (idempotent)."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Area, City, Country, ProductCategory, ProductSettings
from configuration.models import (
    FeesConfiguration,
    ProductCategoryChecklist,
    ReviewChecklistItem,
)

JORDAN = {
    "name_en": "Jordan",
    "name_ar": "الأردن",
    "code": "JO",
}

CITIES = [
    {"name_en": "Amman", "name_ar": "عمان"},
    {"name_en": "Irbid", "name_ar": "إربد"},
    {"name_en": "Zarqa", "name_ar": "الزرقاء"},
    {"name_en": "Aqaba", "name_ar": "العقبة"},
]

AREAS_BY_CITY = {
    "Amman": [
        {"name_en": "Abdoun", "name_ar": "عبدون"},
        {"name_en": "Jabal Amman", "name_ar": "جبل عمان"},
        {"name_en": "Shmeisani", "name_ar": "الشميساني"},
        {"name_en": "Marka", "name_ar": "ماركا"},
    ],
    "Irbid": [
        {"name_en": "City Center", "name_ar": "وسط المدينة"},
        {"name_en": "University District", "name_ar": "حي الجامعة"},
    ],
    "Zarqa": [
        {"name_en": "New Zarqa", "name_ar": "الزرقاء الجديدة"},
    ],
    "Aqaba": [
        {"name_en": "Downtown", "name_ar": "وسط العقبة"},
        {"name_en": "South Beach", "name_ar": "الشاطئ الجنوبي"},
    ],
}

CATEGORIES = [
    {
        "name_en": "General goods",
        "name_ar": "سلع عامة",
        "category_type": "general",
        "requires_review": True,
        "requires_transfer_process": False,
        "requires_inspection": False,
        "fees": {
            "name": "General goods fees",
            "bidder_insurance_amount": Decimal("1.00"),
            "seller_insurance_amount": Decimal("2.00"),
            "subscription_amount": Decimal("2.00"),
        },
        "checklist_items": [
            {"key": "photos_clear", "label_en": "Photos are clear", "label_ar": "الصور واضحة"},
            {"key": "title_accurate", "label_en": "Title matches item", "label_ar": "العنوان يطابق المنتج"},
        ],
        "settings": {
            "min_images_count": 2,
            "max_images_count": 8,
            "video_allowed": False,
            "attachments_allowed": False,
            "allowed_extensions_json": ["jpg", "jpeg", "png", "webp"],
            "location_link_enabled": False,
            "min_start_price": Decimal("1.00"),
            "min_bid_increment": Decimal("1.00"),
            "reserve_price_required": False,
            "inspection_required": False,
            "blur_option_enabled": True,
            "delivery_period_days": 7,
            "auction_extension_enabled": True,
            "extension_minutes": 3,
            "extension_trigger_seconds": 60,
        },
    },
    {
        "name_en": "Electronics",
        "name_ar": "إلكترونيات",
        "category_type": "electronics",
        "requires_review": True,
        "requires_transfer_process": False,
        "requires_inspection": False,
        "fees": {
            "name": "Electronics fees",
            "bidder_insurance_amount": Decimal("2.00"),
            "seller_insurance_amount": Decimal("5.00"),
            "subscription_amount": Decimal("5.00"),
        },
        "checklist_items": [
            {"key": "serial_visible", "label_en": "Serial/model visible", "label_ar": "الرقم التسلسلي ظاهر"},
            {"key": "condition_stated", "label_en": "Condition stated", "label_ar": "الحالة موضحة"},
        ],
        "settings": {
            "min_images_count": 3,
            "max_images_count": 12,
            "video_allowed": True,
            "max_video_duration_sec": 120,
            "attachments_allowed": False,
            "allowed_extensions_json": ["jpg", "jpeg", "png", "webp", "mp4"],
            "location_link_enabled": False,
            "min_start_price": Decimal("5.00"),
            "min_bid_increment": Decimal("5.00"),
            "reserve_price_required": False,
            "inspection_required": False,
            "blur_option_enabled": False,
            "delivery_period_days": 5,
            "auction_extension_enabled": True,
            "extension_minutes": 5,
            "extension_trigger_seconds": 90,
        },
    },
    {
        "name_en": "Vehicles",
        "name_ar": "مركبات",
        "category_type": "vehicles",
        "requires_review": True,
        "requires_transfer_process": True,
        "requires_inspection": True,
        "fees": {
            "name": "Vehicles fees",
            "bidder_insurance_amount": Decimal("25.00"),
            "seller_insurance_amount": Decimal("50.00"),
            "subscription_amount": Decimal("25.00"),
        },
        "checklist_items": [
            {
                "key": "ownership_docs",
                "label_en": "Ownership documents listed",
                "label_ar": "مستندات الملكية مذكورة",
            },
            {
                "key": "vin_visible",
                "label_en": "VIN/plate visible in photos",
                "label_ar": "رقم الشاصي/اللوحة ظاهر",
            },
        ],
        "settings": {
            "min_images_count": 5,
            "max_images_count": 20,
            "video_allowed": True,
            "max_video_duration_sec": 180,
            "attachments_allowed": True,
            "allowed_extensions_json": ["jpg", "jpeg", "png", "pdf", "mp4"],
            "location_link_enabled": False,
            "min_start_price": Decimal("500.00"),
            "min_bid_increment": Decimal("50.00"),
            "reserve_price_required": True,
            "inspection_required": True,
            "blur_option_enabled": False,
            "delivery_period_days": 14,
            "auction_extension_enabled": True,
            "extension_minutes": 5,
            "extension_trigger_seconds": 120,
        },
    },
    {
        "name_en": "Real estate",
        "name_ar": "عقارات",
        "category_type": "real_estate",
        "requires_review": True,
        "requires_transfer_process": True,
        "requires_inspection": False,
        "fees": {
            "name": "Real estate fees",
            "bidder_insurance_amount": Decimal("50.00"),
            "seller_insurance_amount": Decimal("100.00"),
            "subscription_amount": Decimal("50.00"),
        },
        "checklist_items": [
            {
                "key": "location_verified",
                "label_en": "Location link or area set",
                "label_ar": "الموقع أو المنطقة محددة",
            },
            {
                "key": "disclosure_complete",
                "label_en": "Legal disclosures complete",
                "label_ar": "الإفصاحات القانونية مكتملة",
            },
        ],
        "settings": {
            "min_images_count": 4,
            "max_images_count": 15,
            "video_allowed": True,
            "max_video_duration_sec": 300,
            "attachments_allowed": True,
            "allowed_extensions_json": ["jpg", "jpeg", "png", "pdf"],
            "location_link_enabled": True,
            "min_start_price": Decimal("1000.00"),
            "min_bid_increment": Decimal("100.00"),
            "reserve_price_required": True,
            "inspection_required": False,
            "blur_option_enabled": False,
            "delivery_period_days": 30,
            "auction_extension_enabled": False,
            "extension_minutes": 5,
            "extension_trigger_seconds": 60,
        },
    },
]


def _sync_checklist(category, items_spec):
    ProductCategoryChecklist.objects.filter(category=category).delete()
    for sort_order, spec in enumerate(items_spec):
        item, _ = ReviewChecklistItem.objects.update_or_create(
            key=spec["key"],
            defaults={
                "label_en": spec["label_en"],
                "label_ar": spec.get("label_ar", spec["label_en"]),
                "sort_order": sort_order,
                "is_active": True,
            },
        )
        ProductCategoryChecklist.objects.create(
            category=category,
            checklist_item=item,
            sort_order=sort_order,
        )


class Command(BaseCommand):
    help = "Seed Jordan countries/cities/areas and sample product categories (idempotent)."

    def handle(self, *args, **options):
        country, created = Country.objects.get_or_create(
            code=JORDAN["code"],
            defaults={
                "name_en": JORDAN["name_en"],
                "name_ar": JORDAN["name_ar"],
                "is_active": True,
            },
        )
        if not created:
            country.name_en = JORDAN["name_en"]
            country.name_ar = JORDAN["name_ar"]
            country.is_active = True
            country.save(update_fields=["name_en", "name_ar", "is_active"])

        city_count = 0
        area_count = 0
        for city_spec in CITIES:
            city, _ = City.objects.update_or_create(
                country=country,
                name_en=city_spec["name_en"],
                defaults={
                    "name_ar": city_spec["name_ar"],
                    "is_active": True,
                },
            )
            city_count += 1
            for area_spec in AREAS_BY_CITY.get(city_spec["name_en"], []):
                Area.objects.update_or_create(
                    city=city,
                    name_en=area_spec["name_en"],
                    defaults={
                        "name_ar": area_spec["name_ar"],
                        "is_active": True,
                    },
                )
                area_count += 1

        category_count = 0
        for entry in CATEGORIES:
            settings_data = entry["settings"]
            fees_data = entry["fees"]
            category_fields = {k: v for k, v in entry.items() if k not in ("settings", "fees", "checklist_items")}
            fees, _ = FeesConfiguration.objects.update_or_create(
                name=fees_data["name"],
                defaults=fees_data,
            )
            category, _ = ProductCategory.objects.update_or_create(
                name_en=category_fields["name_en"],
                defaults={
                    **category_fields,
                    "fees_configuration": fees,
                    "is_active": True,
                },
            )
            if category.fees_configuration_id != fees.id:
                category.fees_configuration = fees
                category.save(update_fields=["fees_configuration"])
            ProductSettings.objects.update_or_create(
                category=category,
                defaults={**settings_data, "is_active": True},
            )
            _sync_checklist(category, entry["checklist_items"])
            category_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog seeded: country={country.code}, "
                f"cities={city_count}, areas={area_count}, categories={category_count}"
            )
        )

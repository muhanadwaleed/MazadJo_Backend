"""Create two sample auctions for local development / QA."""

from datetime import timedelta
from decimal import Decimal
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from auctions.models import Auction
from catalog.models import ProductSettings
from catalog.tests.helpers import create_test_category

User = get_user_model()


DEMO_TITLE_PREFIX = "Demo auction —"


class Command(BaseCommand):
    help = "Ensures catalog fixtures, then creates two published auctions (active window)."

    def handle(self, *args, **options):
        from catalog.models import ProductCategory

        category = ProductCategory.objects.filter(name_en="Demo category").first()
        if category is None:
            category = create_test_category(
                name_ar="تصنيف تجريبي",
                name_en="Demo category",
                category_type="general",
                requires_review=False,
                fees_name="Demo category fees",
            )
        ProductSettings.objects.get_or_create(
            category=category,
            defaults={},
        )

        seller, created = User.objects.get_or_create(
            username="demo_seller",
            defaults={"email": "demo_seller@example.com"},
        )
        if created:
            seller.set_password("demo-seller-pass-99")
            seller.save(update_fields=["password"])

        specs = [
            {
                "title": f"{DEMO_TITLE_PREFIX} vintage wristwatch",
                "description": "Sample listing for UI testing. Stainless model, runs well.",
                "start_price": Decimal("500.00"),
                "min_bid_increment": Decimal("25.00"),
            },
            {
                "title": f"{DEMO_TITLE_PREFIX} desk lamp",
                "description": "Second sample auction with a lower opening price.",
                "start_price": Decimal("40.00"),
                "min_bid_increment": Decimal("5.00"),
            },
        ]

        created_ids = []
        for spec in specs:
            if Auction.objects.filter(title=spec["title"]).exists():
                self.stdout.write(
                    self.style.WARNING(f"Skip (already exists): {spec['title']!r}")
                )
                continue
            now = timezone.now()
            auction = Auction.objects.create(
                seller=seller,
                product_category=category,
                auction_number=uuid.uuid4().hex[:12].upper(),
                title=spec["title"],
                description=spec["description"],
                status=Auction.Status.ACTIVE,
                start_price=spec["start_price"],
                current_price=spec["start_price"],
                min_bid_increment=spec["min_bid_increment"],
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(days=7),
                origin_deadline=now + timedelta(days=7),
                extend_deadline=now + timedelta(days=7),
            )
            created_ids.append(auction.id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created auction id={auction.id} number={auction.auction_number} "
                    f"title={auction.title!r}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"Done. Auction ids: {created_ids}. Seller: demo_seller")
        )

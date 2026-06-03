from decimal import Decimal

from catalog.models import ProductCategory
from configuration.models import FeesConfiguration


def create_test_category(**kwargs) -> ProductCategory:
    fees_defaults = {
        "name": kwargs.pop("fees_name", "Test fees"),
        "bidder_insurance_amount": kwargs.pop("bidder_insurance", Decimal("0")),
        "seller_insurance_amount": kwargs.pop("seller_insurance", Decimal("0")),
        "subscription_amount": kwargs.pop("subscription_amount", Decimal("1")),
    }
    fees, _ = FeesConfiguration.objects.get_or_create(
        name=fees_defaults["name"],
        defaults=fees_defaults,
    )
    return ProductCategory.objects.create(
        fees_configuration=fees,
        **kwargs,
    )

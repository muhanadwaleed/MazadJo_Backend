from decimal import Decimal

from django.db import migrations


def migrate_fees_and_checklists(apps, schema_editor):
    ProductCategory = apps.get_model("catalog", "ProductCategory")
    ProductSettings = apps.get_model("catalog", "ProductSettings")
    FeesConfiguration = apps.get_model("configuration", "FeesConfiguration")
    ReviewChecklistItem = apps.get_model("configuration", "ReviewChecklistItem")
    ProductCategoryChecklist = apps.get_model("configuration", "ProductCategoryChecklist")

    fee_by_amount = {}
    for ps in ProductSettings.objects.select_related("category").all():
        category = ps.category
        amount = ps.subscription_fee
        if amount not in fee_by_amount:
            fee_by_amount[amount] = FeesConfiguration.objects.create(
                name=f"Default fees ({amount})",
                bidder_insurance_amount=Decimal("0"),
                seller_insurance_amount=Decimal("0"),
                subscription_amount=amount,
            )
        category.fees_configuration = fee_by_amount[amount]
        category.save(update_fields=["fees_configuration"])

        schema = ps.review_checklist_schema_json or {}
        items = schema.get("items") if isinstance(schema, dict) else []
        if not isinstance(items, list):
            items = []
        for sort_order, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            key = (raw.get("key") or "").strip()
            if not key:
                continue
            label_en = raw.get("label_en") or raw.get("label") or key
            label_ar = raw.get("label_ar") or label_en
            item, _ = ReviewChecklistItem.objects.get_or_create(
                key=key,
                defaults={
                    "label_en": label_en[:512],
                    "label_ar": label_ar[:512],
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
            ProductCategoryChecklist.objects.get_or_create(
                category=category,
                checklist_item=item,
                defaults={"sort_order": sort_order},
            )

    for category in ProductCategory.objects.filter(fees_configuration__isnull=True):
        default_fee, _ = FeesConfiguration.objects.get_or_create(
            name="Default fees",
            defaults={
                "bidder_insurance_amount": Decimal("0"),
                "seller_insurance_amount": Decimal("0"),
                "subscription_amount": Decimal("0"),
            },
        )
        category.fees_configuration = default_fee
        category.save(update_fields=["fees_configuration"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_productcategory_fees_configuration_and_more"),
        ("configuration", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_fees_and_checklists, migrations.RunPython.noop),
    ]

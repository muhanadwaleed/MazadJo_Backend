from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_migrate_configuration_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="productsettings",
            name="review_checklist_schema_json",
        ),
        migrations.RemoveField(
            model_name="productsettings",
            name="subscription_fee",
        ),
    ]

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_remove_legacy_product_settings_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productcategory",
            name="fees_configuration",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="categories",
                to="configuration.feesconfiguration",
            ),
        ),
    ]

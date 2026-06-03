import django.db.models.deletion
from django.conf import settings
from django.db import connection, migrations, models


def add_source_item_column(apps, schema_editor):
    table = "auction_review_checklist"
    column = "source_item_id"
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
        if any(col.name == column for col in description):
            return
    if schema_editor.connection.vendor == "sqlite":
        schema_editor.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} integer NULL "
            f"REFERENCES review_checklist_items(id)"
        )
    else:
        schema_editor.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} bigint NULL "
            f"REFERENCES review_checklist_items(id) DEFERRABLE INITIALLY DEFERRED"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("auctions", "0003_delete_auctionreviewchecklist"),
        ("configuration", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="AuctionReviewChecklist",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("checklist_item_key", models.CharField(max_length=128)),
                        ("checklist_item_label", models.CharField(max_length=512)),
                        ("is_checked", models.BooleanField(default=False)),
                        ("checked_at", models.DateTimeField(blank=True, null=True)),
                        (
                            "auction",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="review_checklist_items",
                                to="auctions.auction",
                            ),
                        ),
                        (
                            "checked_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="auction_checklist_checks",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "source_item",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="auction_snapshots",
                                to="configuration.reviewchecklistitem",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "auction_review_checklist",
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("auction", "checklist_item_key"),
                                name="uniq_auction_checklist_key",
                            )
                        ],
                    },
                ),
            ],
            database_operations=[
                migrations.RunPython(add_source_item_column, migrations.RunPython.noop),
            ],
        ),
    ]

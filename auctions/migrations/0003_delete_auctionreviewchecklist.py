from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("auctions", "0002_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name="AuctionReviewChecklist",
                ),
            ],
            database_operations=[],
        ),
    ]

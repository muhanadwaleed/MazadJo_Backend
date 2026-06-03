from django.db.models import F


def increment_user_public_bid_count(*, user_id: int) -> None:
    from accounts.models import UserStats

    UserStats.objects.get_or_create(user_id=user_id)
    UserStats.objects.filter(user_id=user_id).update(total_bids=F("total_bids") + 1)

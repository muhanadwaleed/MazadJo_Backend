from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from auctions.models import Auction


@receiver(pre_save, sender=Auction)
def _auction_cache_prev_winner(sender, instance: Auction, **kwargs) -> None:
    if not instance.pk:
        instance._pre_save_winner_user_id = None
        return
    try:
        old = Auction.objects.only("winner_user_id").get(pk=instance.pk)
        instance._pre_save_winner_user_id = old.winner_user_id
    except Auction.DoesNotExist:
        instance._pre_save_winner_user_id = None


@receiver(post_save, sender=Auction)
def _auction_bump_winner_stats(
    sender, instance: Auction, created: bool, **kwargs
) -> None:
    prev = getattr(instance, "_pre_save_winner_user_id", None)
    new = instance.winner_user_id
    if new and new != prev:
        from accounts.models import UserStats

        UserStats.objects.get_or_create(user_id=new)
        UserStats.objects.filter(user_id=new).update(total_wins=F("total_wins") + 1)
    if prev and prev != new:
        from accounts.models import UserStats

        UserStats.objects.get_or_create(user_id=prev)
        UserStats.objects.filter(user_id=prev).update(
            total_wins=Greatest(F("total_wins") - 1, Value(0)),
        )

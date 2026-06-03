from django.core.exceptions import ValidationError
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from configuration.models import FeesConfiguration


@receiver(pre_delete, sender=FeesConfiguration)
def prevent_orphan_fees_configuration(sender, instance, **kwargs):
    if instance.categories.exists():
        raise ValidationError(
            "Cannot delete a fees configuration that still has product categories. "
            "Reassign categories first."
        )

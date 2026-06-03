from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class FeesConfiguration(models.Model):
    name = models.CharField(max_length=128)
    bidder_insurance_amount = models.DecimalField(max_digits=12, decimal_places=2)
    seller_insurance_amount = models.DecimalField(max_digits=12, decimal_places=2)
    subscription_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fees_configurations"

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.pk and not self.categories.exists():
            raise ValidationError(
                "A fees configuration must have at least one product category."
            )


class TermsAndConditions(models.Model):
    version = models.CharField(max_length=32, unique=True)
    title_ar = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255)
    body_ar = models.TextField()
    body_en = models.TextField()
    is_active = models.BooleanField(default=False, db_index=True)
    effective_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "terms_and_conditions"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="uniq_active_terms",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.version} ({'active' if self.is_active else 'inactive'})"

    def save(self, *args, **kwargs):
        if self.is_active:
            TermsAndConditions.objects.filter(is_active=True).exclude(
                pk=self.pk
            ).update(is_active=False)
        super().save(*args, **kwargs)


class ReviewChecklistItem(models.Model):
    key = models.SlugField(max_length=128, unique=True)
    label_ar = models.CharField(max_length=512)
    label_en = models.CharField(max_length=512)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "review_checklist_items"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.key


class ProductCategoryChecklist(models.Model):
    category = models.ForeignKey(
        "catalog.ProductCategory",
        on_delete=models.CASCADE,
        related_name="category_checklist_links",
    )
    checklist_item = models.ForeignKey(
        ReviewChecklistItem,
        on_delete=models.CASCADE,
        related_name="category_links",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "product_category_checklists"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "checklist_item"],
                name="uniq_category_checklist_item",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.category_id} — {self.checklist_item_id}"


class AuctionReviewChecklist(models.Model):
    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="review_checklist_items",
    )
    source_item = models.ForeignKey(
        ReviewChecklistItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auction_snapshots",
    )
    checklist_item_key = models.CharField(max_length=128)
    checklist_item_label = models.CharField(max_length=512)
    is_checked = models.BooleanField(default=False)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auction_checklist_checks",
    )
    checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auction_review_checklist"
        constraints = [
            models.UniqueConstraint(
                fields=["auction", "checklist_item_key"],
                name="uniq_auction_checklist_key",
            ),
        ]

    def __str__(self) -> str:
        return self.checklist_item_key

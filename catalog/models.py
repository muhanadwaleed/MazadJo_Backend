from django.db import models


class Country(models.Model):
    name_ar = models.CharField(max_length=128)
    name_en = models.CharField(max_length=128)
    code = models.CharField(max_length=3, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "countries"
        verbose_name_plural = "countries"

    def __str__(self) -> str:
        return self.name_en


class City(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="cities"
    )
    name_ar = models.CharField(max_length=128)
    name_en = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "cities"
        verbose_name_plural = "cities"

    def __str__(self) -> str:
        return self.name_en


class Area(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="areas")
    name_ar = models.CharField(max_length=128)
    name_en = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "areas"

    def __str__(self) -> str:
        return self.name_en


class ProductCategory(models.Model):
    name_ar = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)
    category_type = models.CharField(max_length=64, blank=True)
    requires_review = models.BooleanField(default=True)
    requires_transfer_process = models.BooleanField(default=False)
    requires_inspection = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    fees_configuration = models.ForeignKey(
        "configuration.FeesConfiguration",
        on_delete=models.PROTECT,
        related_name="categories",
    )
    review_checklist_items = models.ManyToManyField(
        "configuration.ReviewChecklistItem",
        through="configuration.ProductCategoryChecklist",
        related_name="categories",
        blank=True,
    )

    class Meta:
        db_table = "product_categories"

    def __str__(self) -> str:
        return self.name_en


class ProductSettings(models.Model):
    category = models.OneToOneField(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    min_images_count = models.PositiveSmallIntegerField(default=1)
    max_images_count = models.PositiveSmallIntegerField(default=10)
    video_allowed = models.BooleanField(default=False)
    max_video_duration_sec = models.PositiveIntegerField(null=True, blank=True)
    attachments_allowed = models.BooleanField(default=False)
    allowed_extensions_json = models.JSONField(default=list, blank=True)
    location_link_enabled = models.BooleanField(default=False)
    min_start_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_bid_increment = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    reserve_price_required = models.BooleanField(default=False)
    inspection_required = models.BooleanField(default=False)
    blur_option_enabled = models.BooleanField(default=False)
    delivery_period_days = models.PositiveSmallIntegerField(default=7)
    auction_extension_enabled = models.BooleanField(default=False)
    extension_minutes = models.PositiveSmallIntegerField(default=5)
    extension_trigger_seconds = models.PositiveSmallIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "product_settings"

    def __str__(self) -> str:
        return f"Settings for {self.category_id}"

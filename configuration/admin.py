from django.contrib import admin

from configuration.models import (
    AuctionReviewChecklist,
    FeesConfiguration,
    ProductCategoryChecklist,
    ReviewChecklistItem,
    TermsAndConditions,
)


class ProductCategoryChecklistInline(admin.TabularInline):
    model = ProductCategoryChecklist
    extra = 1


@admin.register(FeesConfiguration)
class FeesConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "bidder_insurance_amount",
        "seller_insurance_amount",
        "subscription_amount",
        "updated_at",
    )
    search_fields = ("name",)


@admin.register(TermsAndConditions)
class TermsAndConditionsAdmin(admin.ModelAdmin):
    list_display = ("version", "title_en", "is_active", "effective_at")
    list_filter = ("is_active",)


@admin.register(ReviewChecklistItem)
class ReviewChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("key", "label_en", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("key", "label_en", "label_ar")


@admin.register(ProductCategoryChecklist)
class ProductCategoryChecklistAdmin(admin.ModelAdmin):
    list_display = ("category", "checklist_item", "sort_order")
    list_filter = ("category",)


@admin.register(AuctionReviewChecklist)
class AuctionReviewChecklistAdmin(admin.ModelAdmin):
    list_display = ("auction", "checklist_item_key", "is_checked", "checked_at")
    list_filter = ("is_checked",)

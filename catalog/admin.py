from django.contrib import admin

from catalog.models import Area, City, Country, ProductCategory, ProductSettings


class CityInline(admin.TabularInline):
    model = City
    extra = 0
    fields = ("name_en", "name_ar", "is_active")


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_ar", "code")
    inlines = [CityInline]


class AreaInline(admin.TabularInline):
    model = Area
    extra = 0
    fields = ("name_en", "name_ar", "is_active")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name_en", "country", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("name_en", "name_ar")
    autocomplete_fields = ("country",)
    inlines = [AreaInline]


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name_en", "city", "is_active")
    list_filter = ("city__country", "city", "is_active")
    search_fields = ("name_en", "name_ar")
    autocomplete_fields = ("city",)


class ProductSettingsInline(admin.StackedInline):
    model = ProductSettings
    can_delete = False
    extra = 0


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name_en",
        "category_type",
        "fees_configuration",
        "requires_review",
        "is_active",
    )
    autocomplete_fields = ("fees_configuration",)
    list_filter = (
        "category_type",
        "requires_review",
        "requires_transfer_process",
        "is_active",
    )
    search_fields = ("name_en", "name_ar", "category_type")
    inlines = [ProductSettingsInline]


@admin.register(ProductSettings)
class ProductSettingsAdmin(admin.ModelAdmin):
    list_display = ("category", "min_start_price", "is_active")
    list_filter = ("is_active", "auction_extension_enabled", "video_allowed")
    search_fields = ("category__name_en",)
    autocomplete_fields = ("category",)

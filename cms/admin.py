from django.contrib import admin

from cms.models import ContactUs, FAQ, WhoUs, WhyUs


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question_en", "sort_order", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("question_en", "question_ar")


@admin.register(WhoUs)
class WhoUsAdmin(admin.ModelAdmin):
    list_display = ("title_en", "sort_order", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(WhyUs)
class WhyUsAdmin(admin.ModelAdmin):
    list_display = ("title_en", "sort_order", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "is_active", "updated_at")
    list_filter = ("is_active",)

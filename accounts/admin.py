from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import UserFingerprint, UserRiskScore, UserStats

User = get_user_model()


class UserRiskScoreInline(admin.StackedInline):
    model = UserRiskScore
    can_delete = False
    max_num = 1
    min_num = 0
    fk_name = "user"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = (UserRiskScoreInline,)
    list_display = (*DjangoUserAdmin.list_display, "is_shadow_banned")
    list_filter = (*DjangoUserAdmin.list_filter, "is_shadow_banned", "user_type")


@admin.register(UserFingerprint)
class UserFingerprintAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "device_hash", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "ip_address", "device_hash")
    readonly_fields = ("user", "ip_address", "user_agent", "device_hash", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(UserRiskScore)
class UserRiskScoreAdmin(admin.ModelAdmin):
    list_display = ("user", "score", "last_updated")
    search_fields = ("user__username",)
    readonly_fields = ("last_updated",)


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ("user", "total_bids", "total_wins", "updated_at")
    search_fields = ("user__username",)
    readonly_fields = ("updated_at",)

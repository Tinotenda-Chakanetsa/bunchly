from django.contrib import admin

from .models import (
    Tenant,
    TenantDomain,
    TenantSettings,
    TenantSubscriptionPlan,
    TenantUserMembership,
)


class TenantDomainInline(admin.TabularInline):
    model = TenantDomain
    extra = 0


class TenantSettingsInline(admin.StackedInline):
    model = TenantSettings
    extra = 0
    can_delete = False


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "country", "created_at")
    list_filter = ("is_active", "country")
    search_fields = ("name", "slug", "legal_name")
    inlines = [TenantDomainInline, TenantSettingsInline]


@admin.register(TenantUserMembership)
class TenantUserMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant", "is_owner", "is_active", "joined_at")
    list_filter = ("is_owner", "is_active")
    search_fields = ("user__email", "tenant__name")
    autocomplete_fields = ("tenant", "user")


admin.site.register(TenantSubscriptionPlan)

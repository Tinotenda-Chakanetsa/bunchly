from django.contrib import admin

from .models import EmailLog, InboundEmail, Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "event_key", "tenant", "channel", "is_enabled")
    list_filter = ("channel", "is_enabled", "event_key", "tenant")
    search_fields = ("name", "event_key", "subject")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "tenant", "event_key", "level", "is_read", "created_at")
    list_filter = ("level", "is_read", "event_key", "tenant")
    search_fields = ("title", "recipient__email")
    readonly_fields = [f.name for f in Notification._meta.fields]


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("to_email", "subject", "tenant", "status", "attempts", "sent_at")
    list_filter = ("status", "provider", "event_key", "tenant")
    search_fields = ("to_email", "subject", "provider_message_id")
    readonly_fields = [f.name for f in EmailLog._meta.fields]


@admin.register(InboundEmail)
class InboundEmailAdmin(admin.ModelAdmin):
    list_display = ("from_email", "to_email", "subject", "tenant", "status", "received_at")
    list_filter = ("status", "provider", "tenant")
    search_fields = ("from_email", "to_email", "subject")
    readonly_fields = [f.name for f in InboundEmail._meta.fields]

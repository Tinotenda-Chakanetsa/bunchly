"""Serializers for the notification engine."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import EmailLog, InboundEmail, Notification, NotificationTemplate


class NotificationTemplateSerializer(TenantScopedModelSerializer):
    """A configurable per-event notification template."""

    event_key_display = serializers.CharField(
        source="get_event_key_display", read_only=True
    )

    class Meta:
        model = NotificationTemplate
        fields = [
            "id", "event_key", "event_key_display", "name", "description",
            "channel", "subject", "body", "is_enabled",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_event_key(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = NotificationTemplate.all_objects.filter(
            tenant=tenant, event_key=value
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A template for this event already exists."
            )
        return value


class NotificationSerializer(serializers.ModelSerializer):
    """An in-app notification (read-only to its recipient)."""

    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id", "event_key", "title", "body", "level", "level_display",
            "url", "entity_type", "entity_id", "is_read", "read_at",
            "created_at",
        ]
        read_only_fields = fields


class EmailLogSerializer(serializers.ModelSerializer):
    """A delivery-audit row for one outbound email."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = EmailLog
        fields = [
            "id", "event_key", "to_email", "from_email", "reply_to",
            "subject", "status", "status_display", "provider",
            "provider_message_id", "attempts", "error_message", "sent_at",
            "created_at",
        ]
        read_only_fields = fields


class InboundEmailSerializer(serializers.ModelSerializer):
    """Stored metadata for a received email."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = InboundEmail
        fields = [
            "id", "from_email", "to_email", "subject", "body", "provider",
            "provider_message_id", "received_at", "status", "status_display",
            "matched_entity_type", "matched_entity_id", "processing_note",
            "created_at",
        ]
        read_only_fields = fields


class TestEmailSerializer(serializers.Serializer):
    """Input for the test-email endpoint."""

    to_email = serializers.EmailField()

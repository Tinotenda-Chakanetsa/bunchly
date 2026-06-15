"""Notification-engine API routes."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    EmailLogViewSet,
    InboundEmailViewSet,
    NotificationTemplateViewSet,
    NotificationViewSet,
    email_delivery_webhook,
    inbound_email_webhook,
)

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register(
    "notification-templates", NotificationTemplateViewSet, basename="notification-template"
)
router.register("email-logs", EmailLogViewSet, basename="email-log")
router.register("inbound-emails", InboundEmailViewSet, basename="inbound-email")

urlpatterns = router.urls + [
    path("webhooks/email-delivery/", email_delivery_webhook, name="email-delivery-webhook"),
    path("webhooks/inbound-email/", inbound_email_webhook, name="inbound-email-webhook"),
]

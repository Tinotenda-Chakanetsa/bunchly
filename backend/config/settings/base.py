"""
Base settings shared by all environments.

All environment-specific or secret values are read from environment
variables via django-environ. Nothing organisation-specific, no SMTP
credentials, and no email recipients are hard-coded here.
"""
from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# config/settings/base.py -> config/settings -> config -> backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    CORS_ALLOWED_ORIGINS=(list, []),
)

# Load a .env file if present (local dev convenience; ignored in containers
# where env vars are injected directly).
env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
]

# Bunchly modular apps. Foundation apps are active; remaining modules are
# added as they are implemented (see handoff.md).
LOCAL_APPS = [
    "apps.common",
    "apps.tenants",
    "apps.accounts",
    "apps.audit",
    "apps.organisation",
    "apps.employees",
    "apps.leave",
    "apps.documents",
    "apps.notifications",
    "apps.workflows",
    "apps.reports",
    "apps.education_assistance",
    "apps.payroll",
    "apps.benefits",
    "apps.recruitment",
    "apps.onboarding",
    "apps.performance",
    "apps.learning",
    "apps.assets",
    "apps.helpdesk",
    "apps.attendance",
    "apps.imports",
    "apps.policies",
    "apps.settings",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",  # MFA: marks request.user.is_verified()
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Bunchly request context: attach request id, then resolve tenant.
    "apps.common.middleware.RequestContextMiddleware",
    "apps.common.middleware.TenantMiddleware",
    "apps.common.middleware.SecurityMonitorMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://bunchly:bunchly@localhost:5432/bunchly",
    ),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# Argon2id (RFC 9106) as the primary hasher — fast, memory-hard, and the
# OWASP-recommended default. PBKDF2 / bcrypt remain in the list so
# existing hashes verify and re-hash transparently on next login.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Account lockout (enforced by the auth views).
LOGIN_MAX_FAILED_ATTEMPTS = env.int("LOGIN_MAX_FAILED_ATTEMPTS", default=5)
LOGIN_LOCKOUT_MINUTES = env.int("LOGIN_LOCKOUT_MINUTES", default=15)

# ---------------------------------------------------------------------------
# Caching / Redis
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    },
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TIME_LIMIT = 60 * 30
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TIMEZONE = env("TIME_ZONE", default="UTC")

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.TenantJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.bunchly_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": env("THROTTLE_USER", default="1000/hour"),
        "anon": env("THROTTLE_ANON", default="100/hour"),
        "login": env("THROTTLE_LOGIN", default="10/min"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="5/min"),
        "invitation": env("THROTTLE_INVITATION", default="20/hour"),
        "upload": env("THROTTLE_UPLOAD", default="60/min"),
        "export": env("THROTTLE_EXPORT", default="20/hour"),
        "email_test": env("THROTTLE_EMAIL_TEST", default="5/min"),
        "public_application": env("THROTTLE_PUBLIC_APPLICATION", default="10/hour"),
    },
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_MINUTES", default=30)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": env("JWT_SECRET", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Bunchly HRMS API",
    "DESCRIPTION": "Bring your people, processes, and payroll together.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
# The frontend attaches X-Tenant-ID on every request to pick the active
# tenant; django-cors-headers' default header allowlist doesn't include
# custom names, so the browser would reject the preflight without this.
CORS_ALLOW_HEADERS = (*default_headers, "x-tenant-id")

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# File-storage backend: "local" or "s3". S3 keeps uploads off ephemeral
# container storage in production.
FILE_STORAGE_BACKEND = env("FILE_STORAGE_BACKEND", default="local")
if FILE_STORAGE_BACKEND == "s3":
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="")
    AWS_QUERYSTRING_AUTH = True  # signed URLs for private documents
    AWS_DEFAULT_ACL = None

# Upload validation defaults (configurable per tenant at runtime).
MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=15)
ALLOWED_UPLOAD_EXTENSIONS = env(
    "ALLOWED_UPLOAD_EXTENSIONS",
    default="pdf,docx,jpg,jpeg,png",
).split(",")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email (configurable — never hard-coded)
# ---------------------------------------------------------------------------
EMAIL_PROVIDER = env("EMAIL_PROVIDER", default="smtp")  # "resend" or "smtp"
RESEND_API_KEY = env("RESEND_API_KEY", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@bunchly.local")
DEFAULT_REPLY_TO_EMAIL = env("DEFAULT_REPLY_TO_EMAIL", default="")
EMAIL_HOST = env("SMTP_HOST", default="")
EMAIL_PORT = env.int("SMTP_PORT", default=587)
EMAIL_HOST_USER = env("SMTP_USERNAME", default="")
EMAIL_HOST_PASSWORD = env("SMTP_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("SMTP_USE_TLS", default=True)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Shared secret for provider webhook callbacks (delivery events, inbound
# email). Webhook endpoints fail closed when this is unset.
NOTIFICATIONS_WEBHOOK_SECRET = env("NOTIFICATIONS_WEBHOOK_SECRET", default="")

# ---------------------------------------------------------------------------
# Security headers (HTTPS-ready; tightened in prod.py)
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Cap upload size on the Django side so a single huge body can't OOM
# the worker before our document validators run.
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024 if False else 25 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Centralised list of fields the masking helpers should consider
# sensitive. Endpoint serializers that don't explicitly grant
# clearance render these as masked strings (see apps.common.masking).
SENSITIVE_FIELDS = {
    "salary",
    "base_salary",
    "current_salary",
    "annual_salary",
    "bank_account_number",
    "bank_account",
    "bank_routing",
    "iban",
    "national_id",
    "national_id_number",
    "passport_number",
    "tax_number",
    "tax_id",
    "medical_notes",
    "disciplinary_notes",
    "dependant_id",
    "child_id_number",
}

# Permissions that unlock sensitive-field clearance per module. A serializer
# checks `request.user.has_perm_code(...)` against this map to decide
# whether to mask or reveal.
SENSITIVE_FIELD_PERMISSIONS = {
    "salary": "payroll.view_salary",
    "base_salary": "payroll.view_salary",
    "current_salary": "payroll.view_salary",
    "annual_salary": "payroll.view_salary",
    "bank_account_number": "payroll.view_bank_details",
    "bank_account": "payroll.view_bank_details",
    "bank_routing": "payroll.view_bank_details",
    "iban": "payroll.view_bank_details",
    "national_id": "employees.view_pii",
    "national_id_number": "employees.view_pii",
    "passport_number": "employees.view_pii",
    "tax_number": "employees.view_pii",
    "tax_id": "employees.view_pii",
    "medical_notes": "employees.view_medical",
    "disciplinary_notes": "employees.view_disciplinary",
}

# Signed URLs: how long a document download link stays valid for.
DOCUMENT_SIGNED_URL_TTL_SECONDS = env.int(
    "DOCUMENT_SIGNED_URL_TTL_SECONDS", default=300
)

# Suspicious-activity thresholds.
SECURITY_BULK_EXPORT_THRESHOLD = env.int(
    "SECURITY_BULK_EXPORT_THRESHOLD", default=5
)
SECURITY_BULK_EXPORT_WINDOW_SECONDS = env.int(
    "SECURITY_BULK_EXPORT_WINDOW_SECONDS", default=600
)

# ---------------------------------------------------------------------------
# Logging — structured JSON to stdout (container-friendly)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "plain": {"format": "[%(asctime)s] %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": env("LOG_FORMAT", default="json"),
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "bunchly": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "bunchly.audit": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

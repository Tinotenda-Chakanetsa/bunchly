"""Development settings."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Permissive CORS for local frontend dev servers.
CORS_ALLOW_ALL_ORIGINS = True

# In dev, use the simpler whitenoise storage (no hashed-filename
# manifest). The manifest variant is brittle to interrupted writes —
# a partial staticfiles.json crashes the next boot — and offers no
# real benefit locally. Prod still uses the manifest storage from base.
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
}

# In dev, print emails to the console unless a provider is configured.
if not env("RESEND_API_KEY", default="") and not env("SMTP_HOST", default=""):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Browsable API is handy in development.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# System dependencies (psycopg build + healthcheck client).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (cached layer).
COPY requirements/ requirements/
RUN pip install --upgrade pip && pip install -r requirements/prod.txt

# Application code.
COPY . .

# Run as a non-root user. The chmod on entrypoint.sh re-applies the
# executable bit, which git-on-Windows / rsync-without-chmod silently
# drops during transfer to a Linux host.
RUN useradd --create-home --uid 1000 bunchly \
    && mkdir -p /app/staticfiles /app/media \
    && chmod +x /app/entrypoint.sh \
    && chown -R bunchly:bunchly /app
USER bunchly

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["web"]

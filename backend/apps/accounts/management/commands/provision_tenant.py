"""Provision a new tenant + its first Organisation Administrator.

Thin CLI wrapper over ``apps.tenants.services.provision_tenant`` — the
same code path the platform-admin UI calls. Idempotent on
``--slug``/``--admin-email``.

Examples
--------
  python manage.py provision_tenant \\
      --name "Acme Holdings" \\
      --slug acme-holdings \\
      --domain acme.bunchly.app \\
      --admin-email owner@acme.example \\
      --admin-password 'change-me-on-first-login'

  python manage.py provision_tenant \\
      --name "Beta Industries" \\
      --slug beta \\
      --admin-email founder@beta.example
      # No password supplied -> random one is printed once.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.services import provision_tenant


class Command(BaseCommand):
    help = "Create a new tenant and its first administrator user."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--name", required=True, help="Organisation display name.")
        parser.add_argument("--slug", help="URL slug. Defaults to slugified --name.")
        parser.add_argument("--domain", help="Primary domain. Defaults to <slug>.bunchly.local.")
        parser.add_argument("--country", default="", help="Country (optional).")
        parser.add_argument("--legal-name", default="", help="Legal name (optional).")
        parser.add_argument("--industry", default="", help="Industry (optional).")
        parser.add_argument("--admin-email", required=True, help="First admin email.")
        parser.add_argument("--admin-first", default="", help="Admin first name (optional).")
        parser.add_argument("--admin-last", default="", help="Admin last name (optional).")
        parser.add_argument(
            "--admin-password",
            help="Admin password. Random one printed once if omitted.",
        )

    def handle(self, *args, **opts):
        try:
            result = provision_tenant(
                name=opts["name"],
                slug=opts.get("slug"),
                domain=opts.get("domain"),
                country=opts.get("country") or "",
                legal_name=opts.get("legal_name") or "",
                industry=opts.get("industry") or "",
                admin_email=opts["admin_email"],
                admin_first_name=opts.get("admin_first") or "",
                admin_last_name=opts.get("admin_last") or "",
                admin_password=opts.get("admin_password"),
            )
        except ValueError as exc:
            raise CommandError(str(exc))

        action = "Created" if result.tenant_created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} tenant '{result.tenant.name}' ({result.tenant.slug})")
        )
        primary = result.tenant.domains.filter(is_primary=True).first()
        if primary:
            self.stdout.write(f"  primary domain: {primary.domain}")
        self.stdout.write(self.style.SUCCESS(f"  admin user: {result.admin.email}"))
        if result.admin_password:
            self.stdout.write(
                self.style.WARNING(
                    f"  one-time password (save this now): {result.admin_password}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"\nTenant '{result.tenant.name}' is ready. Sign in at the frontend "
                f"with {result.admin.email} to start onboarding employees."
            )
        )

"""Seed the RBAC catalogue: permissions and system role templates.

Idempotent — safe to run on every deploy. System roles are stored with
``tenant=None``; provisioning a tenant copies them in. Pass
``--refresh-tenants`` to push any new permissions into every tenant's
copies of the system roles (use this after editing
``constants.DEFAULT_ROLES``).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.constants import DEFAULT_ROLES, PERMISSIONS
from apps.accounts.models import Permission, Role


class Command(BaseCommand):
    help = "Create/update RBAC permissions and system role templates."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--refresh-tenants",
            action="store_true",
            help=(
                "Also propagate the latest system-role permissions into every "
                "tenant's copy of the role (preserves custom roles)."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        created_perms = 0
        for code, name, module in PERMISSIONS:
            _, created = Permission.objects.update_or_create(
                code=code, defaults={"name": name, "module": module}
            )
            created_perms += int(created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Permissions: {Permission.objects.count()} total "
                f"({created_perms} new)."
            )
        )

        for role_name, cfg in DEFAULT_ROLES.items():
            role, _ = Role.objects.update_or_create(
                tenant=None,
                name=role_name,
                defaults={"description": cfg["description"], "is_system": True},
            )
            codes = cfg["permissions"]
            if codes == ["*"]:
                perms = Permission.objects.all()
            else:
                perms = Permission.objects.filter(code__in=codes)
            role.permissions.set(perms)

        self.stdout.write(
            self.style.SUCCESS(
                f"System roles: {Role.objects.filter(tenant=None).count()} ready."
            )
        )

        if options["refresh_tenants"]:
            refreshed = 0
            for role_name, cfg in DEFAULT_ROLES.items():
                codes = cfg["permissions"]
                perms = (
                    Permission.objects.all()
                    if codes == ["*"]
                    else Permission.objects.filter(code__in=codes)
                )
                # Update every tenant copy that has the same name. Custom
                # roles created per-tenant are left alone.
                for tenant_role in Role.objects.filter(
                    tenant__isnull=False, name=role_name, is_system=True
                ):
                    tenant_role.permissions.set(perms)
                    refreshed += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Refreshed {refreshed} tenant role copy/copies."
                )
            )

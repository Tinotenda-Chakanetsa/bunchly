"""Enable PostgreSQL row-level security on every tenant-scoped table.

This migration introspects ``information_schema`` to find every base
table in the ``public`` schema that has a ``tenant_id`` column, then
attaches an RLS policy that limits access to rows whose ``tenant_id``
matches the runtime setting ``app.tenant_id``.

The middleware / DRF authentication layer
(``apps.common.db.set_tenant_setting``) sets this variable to the
authenticated user's tenant on every API request. So even if a viewset
forgets to call ``.filter(tenant=...)``, the database physically
refuses to return another tenant's rows.

The policy also includes a *bypass* arm when ``app.tenant_id`` is
unset (e.g. during ``manage.py migrate``, ``shell``, Celery jobs that
intentionally cross tenants for system operations) so that operations
not running inside a per-tenant HTTP request continue to work.

Forward / reverse SQL is generated dynamically because the migration
must apply to tables created by any other app's own migrations — we
don't want to maintain a hard-coded list that drifts.
"""
from __future__ import annotations

from django.db import migrations


FORWARD_SQL = r"""
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT c.table_schema, c.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
            USING (table_schema, table_name)
        WHERE c.column_name = 'tenant_id'
          AND c.table_schema = 'public'
          AND t.table_type = 'BASE TABLE'
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY;',
            r.table_schema, r.table_name
        );
        EXECUTE format(
            'DROP POLICY IF EXISTS bunchly_tenant_isolation ON %I.%I;',
            r.table_schema, r.table_name
        );
        EXECUTE format(
            'CREATE POLICY bunchly_tenant_isolation ON %I.%I '
            'USING ('
            '  current_setting(''app.tenant_id'', true) IS NULL '
            '  OR current_setting(''app.tenant_id'', true) = '''' '
            '  OR tenant_id::text = current_setting(''app.tenant_id'', true)'
            ') '
            'WITH CHECK ('
            '  current_setting(''app.tenant_id'', true) IS NULL '
            '  OR current_setting(''app.tenant_id'', true) = '''' '
            '  OR tenant_id::text = current_setting(''app.tenant_id'', true)'
            ');',
            r.table_schema, r.table_name
        );
    END LOOP;
END$$;
"""

REVERSE_SQL = r"""
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT n.nspname AS table_schema, c.relname AS table_name
        FROM pg_policy p
        JOIN pg_class c ON c.oid = p.polrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE p.polname = 'bunchly_tenant_isolation'
    LOOP
        EXECUTE format(
            'DROP POLICY IF EXISTS bunchly_tenant_isolation ON %I.%I;',
            r.table_schema, r.table_name
        );
        EXECUTE format(
            'ALTER TABLE %I.%I DISABLE ROW LEVEL SECURITY;',
            r.table_schema, r.table_name
        );
    END LOOP;
END$$;
"""


def _is_postgres(schema_editor) -> bool:
    return schema_editor.connection.vendor == "postgresql"


def _enable(apps, schema_editor):
    if not _is_postgres(schema_editor):
        return
    # Use the raw cursor (not schema_editor.execute) so the SQL is not
    # passed through psycopg's parameterised mogrify pass — our SQL
    # contains literal % characters inside Postgres ``format(%I, ...)``
    # calls that psycopg would otherwise misinterpret as placeholders.
    with schema_editor.connection.cursor() as cur:
        cur.execute(FORWARD_SQL)


def _disable(apps, schema_editor):
    if not _is_postgres(schema_editor):
        return
    with schema_editor.connection.cursor() as cur:
        cur.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    """Runs after every other app's initial migrations have built the
    tenant-scoped tables so the introspection covers all of them."""

    dependencies = [
        ("tenants", "0001_initial"),
        ("employees", "0001_initial"),
        ("leave", "0001_initial"),
        ("documents", "0001_initial"),
        ("education_assistance", "0001_initial"),
        ("payroll", "0001_initial"),
        ("benefits", "0001_initial"),
        ("recruitment", "0001_initial"),
        ("onboarding", "0001_initial"),
        ("performance", "0001_initial"),
        ("learning", "0001_initial"),
        ("assets", "0001_initial"),
        ("audit", "0001_initial"),
        ("organisation", "0001_initial"),
        ("attendance", "0001_initial"),
        ("policies", "0001_initial"),
        ("helpdesk", "0001_initial"),
        ("workflows", "0001_initial"),
        ("notifications", "0001_initial"),
        ("system_settings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_enable, _disable),
    ]

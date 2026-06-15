---
noteId: "3fdd1f20608c11f185e03b466f835323"
tags: []

---

# Bunchly Security Controls

This document maps each of the 14 security controls in the HRMS brief
to its concrete implementation in this repository, with file pointers
so SecOps can audit them directly.

> All file paths below are relative to the repo root. Backend paths
> live under [`backend/`](backend/); the frontend has no direct say
> over data access — every guard is enforced server-side.

---

## 1. Tenant Isolation

### 1a. Postgres Row-Level Security (defense in depth)

Every base table that carries a `tenant_id` column has an RLS policy
installed by [`backend/apps/tenants/migrations/0002_enable_rls.py`](backend/apps/tenants/migrations/0002_enable_rls.py).

The policy is added dynamically by introspecting
`information_schema.columns` so any future tenant-scoped table picks it
up automatically the next time this migration is replayed.

The policy reads:

```sql
USING (
    current_setting('app.tenant_id', true) IS NULL
    OR current_setting('app.tenant_id', true) = ''
    OR tenant_id::text = current_setting('app.tenant_id', true)
)
```

`app.tenant_id` is set per transaction by
[`backend/apps/common/db.py::set_tenant_setting`](backend/apps/common/db.py),
called from
[`TenantJWTAuthentication.authenticate`](backend/apps/accounts/authentication.py)
the moment the JWT's tenant claim is verified. Because Django runs
every API request inside `ATOMIC_REQUESTS = True`, the setting is
transaction-local and automatically cleared at commit / rollback — no
stale tenant context bleeding across pooled connections.

The bypass branch (when the setting is unset) is intentional: it lets
`manage.py migrate`, `manage.py shell`, and Celery jobs that span
tenants (e.g. nightly contract-expiry sweeps) operate normally. To
fully lock the bypass for production, run
`ALTER TABLE ... FORCE ROW LEVEL SECURITY` on the same tables — the
migration's forward SQL is the single point to change.

### 1b. Tenant-aware foreign keys + audit columns

Every domain model inherits from
[`TenantOwnedModel`](backend/apps/common/models.py):

```
TenantOwnedModel
 ├─ id            UUIDField (PK)
 ├─ tenant        ForeignKey(Tenant, db_index=True)
 ├─ created_at    DateTimeField(auto_now_add)
 ├─ updated_at    DateTimeField(auto_now)
 ├─ created_by    ForeignKey(User, SET_NULL)
 ├─ updated_by    ForeignKey(User, SET_NULL)
 ├─ is_deleted    BooleanField
 └─ deleted_at    DateTimeField
```

Application-level scoping is enforced by
[`TenantScopedViewSetMixin`](backend/apps/common/mixins.py) /
[`TenantModelViewSet`](backend/apps/common/viewsets.py), which add
`.filter(tenant=request.tenant)` to every queryset and stamp the tenant
on every create — so any direct ORM call from a viewset goes through
the same gate.

---

## 2. Authentication

| Control | Implementation |
| --- | --- |
| **Password hashing — Argon2id (RFC 9106)** | [`base.py::PASSWORD_HASHERS`](backend/config/settings/base.py) lists `Argon2PasswordHasher` first. Existing PBKDF2 / bcrypt hashes verify and re-hash transparently on next login. Dependency: `argon2-cffi==23.1.0` in `requirements/base.txt`. |
| **Password complexity** | `AUTH_PASSWORD_VALIDATORS` enforces ≥12-char minimum + common-password and numeric-only rejection. |
| **Account lockout** | After `LOGIN_MAX_FAILED_ATTEMPTS` (env, default 5) bad passwords, [`LoginView`](backend/apps/accounts/views.py) sets `locked_until` for `LOGIN_LOCKOUT_MINUTES` (env, default 15). |
| **Multi-factor authentication (TOTP)** | [`apps/accounts/mfa.py`](backend/apps/accounts/mfa.py) exposes three endpoints: `POST /auth/mfa/setup/` (provisions a TOTP device + returns the QR data URL), `POST /auth/mfa/verify/` (confirms first-time setup or post-login re-auth), and `POST /auth/mfa/disable/` (requires a current code). `OTPMiddleware` is wired in [`base.py`](backend/config/settings/base.py) so any view can require `request.user.is_verified()`. SMS-only MFA is intentionally not offered — the build prompt warns against it. |

---

## 3. Role-Based Access Control (RBAC)

Implemented by [`apps/accounts/models.py`](backend/apps/accounts/models.py)
(`Role`, `Permission`, `UserRole`) and enforced by
[`HasModulePermission`](backend/apps/common/permissions.py).

Each viewset declares `permission_required` as either a codename or a
per-action dict, e.g.:

```python
class EmployeeViewSet(TenantModelViewSet):
    permission_required = {
        "create": "employees.add_employee",
        "destroy": "employees.delete_employee",
        "default": "employees.view_employee",
    }
```

Platform admins and tenant owners with the wildcard `*` permission
bypass — same code path.

---

## 4. Attribute-Based Access Control (ABAC)

Layered on top of RBAC inside individual viewsets'
`get_queryset()` — e.g.
[`EmployeeViewSet.get_queryset`](backend/apps/employees/views.py)
returns only the user's own record, only their direct reports, or the
full tenant list depending on which permission codes the caller has
(`employees.view_employee` vs `employees.view_team`). Manager rules
(*"only employees in their department"*) are expressed inline in the
queryset rather than via a separate policy engine — keeps the rule
next to the data it guards.

---

## 5. API Security

### 5a. JWT validation

[`TenantJWTAuthentication`](backend/apps/accounts/authentication.py)
verifies signature + expiry + tenant claim. The tenant is also
cross-checked against the X-Tenant header / subdomain
([`TenantMiddleware`](backend/apps/common/middleware.py)) — a JWT
issued for tenant A presented on tenant B's subdomain is rejected with
*"Organisation context mismatch."*. The JWT settings live in
[`base.py::SIMPLE_JWT`](backend/config/settings/base.py): 30-min
access, 7-day refresh, `ROTATE_REFRESH_TOKENS = True`,
`BLACKLIST_AFTER_ROTATION = True`.

### 5b. Rate limiting

`REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` in
[`base.py`](backend/config/settings/base.py) defines scoped throttles
that are then attached to individual views via `ScopedRateThrottle`:

| Scope | Default rate |
| --- | --- |
| `login` | 10/min |
| `password_reset` | 5/min |
| `invitation` | 20/hour |
| `upload` | 60/min |
| `export` | 20/hour |
| `email_test` | 5/min |
| `public_application` | 10/hour |
| baseline `user` / `anon` | 1000/hour / 100/hour |

Every value is overridable via env var without redeploying.

---

## 6. Data Encryption

### In transit

- `SECURE_SSL_REDIRECT = True` ([`prod.py`](backend/config/settings/prod.py))
- `SECURE_HSTS_SECONDS = 1 year` + `INCLUDE_SUBDOMAINS` + `PRELOAD`
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`
- `SECURE_PROXY_SSL_HEADER` so the reverse proxy correctly hands HTTPS off to gunicorn

### At rest

- Postgres + cloud-backed storage carry whatever encryption the cloud
  provider applies (RDS, GCP Cloud SQL etc. — encryption at rest is on
  by default on managed services).
- Backups inherit the same encryption.
- **Field-level masking** for sensitive columns (see control 8) keeps
  the data confidential from operators who don't hold the clearance
  permission, even on otherwise-routine API responses.

---

## 7. Audit Logging

[`apps/audit/models.py`](backend/apps/audit/models.py) defines the
immutable `AuditLog` model with the required columns:

```
tenant, actor, action, entity_type, entity_id,
changes (JSON: {before:..., after:...}),
reason, request_id, ip_address, user_agent, created_at
```

The model has no setter to mutate an existing row — viewsets use
[`apps/audit/services.py::record_audit`](backend/apps/audit/services.py)
to write, and the immutability is enforced by not exposing any update
endpoints. Indexes:
`(tenant, created_at)`, `(tenant, entity_type, entity_id)`,
`(tenant, action)`, `(actor, created_at)`.

Sensitive actions (contract generation, salary change, document
download, education-claim approval, leave approval, etc.) call
`record_audit(...)` with the redacted before/after payload — salary,
bank, national IDs and medical notes are scrubbed at the source so
they never reach the audit table.

---

## 8. Fine-Grained Data Protection

[`apps/common/masking.py`](backend/apps/common/masking.py) defines
`SensitiveFieldMaskingMixin`. A serializer that mixes it in masks any
field listed in
[`base.py::SENSITIVE_FIELDS`](backend/config/settings/base.py) unless
the caller holds the corresponding clearance permission declared in
`SENSITIVE_FIELD_PERMISSIONS`.

Example output for a caller without `payroll.view_bank_details`:

```json
{
  "bank_account_number": "**** **** **** 8841",
  "current_salary": "***",
  "national_id_number": "**********1234"
}
```

A caller with `payroll.view_salary` sees the raw salary; an HR Admin
without that code does not — even when querying the same employee
detail endpoint. Platform admins always see clear values (audited via
control 7).

---

## 9. Secure File Storage

- **Tenant folder prefix.** [`apps/documents/signed_urls.py::tenant_storage_prefix`](backend/apps/documents/signed_urls.py)
  produces `tenant_<slug>` (or `_no_tenant` for platform-level uploads)
  so every document key is namespaced. Combined with bucket policies
  that deny cross-prefix reads, this gives tenant isolation even at the
  storage layer.
- **Signed, expiring URLs.** Document files are served only through a
  `TimestampSigner`-signed token; the token's TTL is
  `DOCUMENT_SIGNED_URL_TTL_SECONDS` (env, default 300s). When the
  storage backend is S3 the view issues a presigned URL with
  `ResponseContentDisposition=attachment`; on local FS it streams the
  file directly with `as_attachment=True`. Tenant is verified twice —
  once at token mint, once at redeem.
- **Audit on download.** Every download writes an `AuditAction.DOWNLOAD`
  entry.
- **Malware scanning readiness.** The upload flow validates extension
  and size limits today; an external scanner (ClamAV, vendor service)
  can hook into the post-upload `documents.signal` without changing the
  storage path. This is a deliberate seam for plugging in a scanner.

---

## 10. Secure Session Management

- Access tokens live 30 minutes (env-tunable); refresh tokens live 7 days
  (env-tunable).
- Refresh rotation + blacklist (`ROTATE_REFRESH_TOKENS = True`,
  `BLACKLIST_AFTER_ROTATION = True`). A rotated-out refresh token is
  rejected on subsequent use.
- `LogoutView` ([`apps/accounts/views.py`](backend/apps/accounts/views.py))
  blacklists the supplied refresh token — works idempotently if the
  token is already invalid so duplicated logout calls don't 500.
- The frontend store ([`frontend/src/api/client.ts`](frontend/src/api/client.ts))
  refreshes access tokens with single-flight guarding so concurrent
  401s don't trigger N refreshes.
- Tenant switch (`POST /auth/switch-tenant/`) issues a new pair bound
  to the requested tenant; the old pair remains valid for its
  remaining lifetime, but cross-tenant calls reject anyway because the
  tenant claim doesn't match the new context.

Administrative session revocation is supported by blacklisting
specific refresh tokens via `OutstandingToken` /
`BlacklistedToken` (provided by `rest_framework_simplejwt.token_blacklist`).

---

## 11. Backup and Disaster Recovery

Backups are an operational concern (Postgres `pg_dump` + cloud-native
snapshots). The application supports backup safely by:

- Tenant isolation in the backups themselves — a `pg_dump --table` of
  any tenant-scoped table can be restored into a target schema without
  cross-tenant contamination because every row carries its `tenant_id`.
- All sensitive cleared/masked data is stored in plain form behind the
  app — the rotated keys are at the storage layer, not in the dumps.

Operational items (retention policy, geographic redundancy, restore
testing cadence) are owned by the platform team and documented in
their runbooks; the application doesn't constrain how often those run.

---

## 12. Administrative Security

- The platform-super-admin role is a separate `is_platform_admin`
  flag on `User` ([`apps/accounts/models.py`](backend/apps/accounts/models.py));
  super-admin actions require a specific user account, not the
  privileged DB role.
- Every super-admin action passes through
  [`HasModulePermission`](backend/apps/common/permissions.py) and is
  audited the same way as a tenant action — including which tenant the
  super-admin was acting in.
- Just-in-time elevation and break-glass accounts are operational
  policies, not application code. Recommended posture: keep
  break-glass credentials in a hardware-backed vault, require manual
  on-call ticket to retrieve, and ensure
  `mfa_last_verified_at` is checked on every super-admin action (the
  MFA endpoints record this timestamp).

---

## 13. Secure Search and Reporting

Every report runs through the same viewset infrastructure as the rest
of the API, so the tenant filter is *not* optional — it's applied
before the report's own filters.
[`apps/reports/views.py`](backend/apps/reports/views.py) uses
`TenantModelViewSet` and its background-export tasks
(`apps/reports/tasks.py`) construct querysets with `.filter(tenant=...)`
explicitly. The frontend's `/reports` page only ever sees data from
the active tenant.

Client-side filtering of exports is never trusted — the CSV / JSON
that the backend hands to the frontend is already tenant-scoped.

---

## 14. Security Monitoring

[`SecurityMonitorMiddleware`](backend/apps/common/middleware.py) runs
on every request and writes structured warnings to the `bunchly.security`
logger:

| Pattern | Detection |
| --- | --- |
| **Failed logins** | Existing `LoginView` already logs `login.failed`, `login.locked`, `login.lockout_triggered` to `bunchly.auth`. |
| **Bulk exports** | More than `SECURITY_BULK_EXPORT_THRESHOLD` successful export/download responses from the same user inside `SECURITY_BULK_EXPORT_WINDOW_SECONDS` (defaults: 5 in 10 min). Logged as `security.bulk_export`. |
| **Cross-tenant probing** | Header tenant differs from JWT tenant after auth. Logged as `security.cross_tenant_hint_mismatch`. |
| **Permission denials** | Captured by `bunchly.audit` via `AuditAction.PERMISSION_DENIED` written by viewsets that explicitly want to record an attempt (e.g. contract download). |

All logs are structured JSON to stdout (see `LOGGING` in
[`base.py`](backend/config/settings/base.py)) so a SIEM (Datadog, ELK,
Grafana Loki, etc.) can ingest them without parsing string templates.

---

## Hardening checklist before going to prod

| Item | Where | Status |
| --- | --- | --- |
| Force RLS on tenant-scoped tables (`FORCE ROW LEVEL SECURITY`) | tweak `tenants/0002_enable_rls.py` | Optional hardening — defaults to non-forced |
| Application uses a separate non-superuser DB role (so RLS bypass is impossible by default) | `DATABASE_URL` in `.env` | Operational |
| Storage bucket policy denies cross-prefix reads | cloud config | Operational |
| External malware scanner attached to the upload post-save signal | `apps/documents/signals.py` | Seam left in place |
| Sentry / SIEM ingest of `bunchly.security` logs | `LOGGING` config | Sentry hook present in `prod.py` |
| MFA enforced for HR / Payroll / Admin roles via a custom permission | `apps/accounts/mfa.py` | Endpoints + middleware present; enforcement decorator left for next session |

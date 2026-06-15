---
noteId: "781e1460600b11f1971331274a503594"
tags: []

---

# Bunchly

> Bring your people, processes, and payroll together.

Bunchly is a modular, multi-tenant HRMS / HRIS platform: core HR, employee &
manager self-service, leave, documents, education-assistance claims, payroll
readiness, recruitment, onboarding, performance, learning, assets, HR cases,
reporting and a configurable workflow & notification engine.

This repository contains the production app:

```
/backend       Django + DRF + Celery + Postgres
/frontend      React + TypeScript + Vite + Tailwind
/docker-compose.yml
/.env.example
/handoff.md    Build state & next steps — read this before every session
```

The backend is the working implementation that started life in the reference
folder `../new bunchly backend` and has been copied here; the frontend was
rebuilt from the Daybreak prototype (`./Bunchly frontend redesign`) into a real
Vite + React + TypeScript app.

---

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Frontend: <http://localhost:3001>
- Backend API: <http://localhost:8001/api/v1/>
- API docs (Swagger): <http://localhost:8001/api/docs/>
- Django admin: <http://localhost:8001/admin/>

Bootstrap demo data (seeds RBAC, a tenant, and a few employees):

```bash
docker compose run --rm backend bootstrap
```

Sign in with one of the seeded users (printed at the end of `bootstrap_demo`).

### Adding a new tenant (organisation)

Bunchly is multi-tenant — each customer organisation gets its own
isolated set of employees, leave records, claims and so on. To
provision one, run the `provision_tenant` management command:

```bash
docker compose run --rm backend python manage.py provision_tenant \
  --name "Acme Holdings" \
  --slug acme-holdings \
  --domain acme.bunchly.app \
  --admin-email owner@acme.example \
  --admin-password 'change-me-on-first-login'
```

This creates the tenant, its TenantSettings + primary domain, copies
every system RBAC role in, then creates the first user with the
**Organisation Administrator** role. If you omit `--admin-password`, a
random one is generated and printed once. The new admin can then sign
in at <http://localhost:3100> and add employees, configure benefits,
invite users, etc.

For the demo stack the command is idempotent — re-running with the
same `--slug`/`--admin-email` just refreshes the domain + admin role
membership (and resets the password if you pass a new one).

### Updating role permissions after editing `constants.DEFAULT_ROLES`

When `apps/accounts/constants.py::DEFAULT_ROLES` changes, the system
templates need re-seeding *and* every existing tenant's copies need to
pick up the new permission set:

```bash
docker compose run --rm backend python manage.py seed_rbac --refresh-tenants
```

Without `--refresh-tenants` only the system templates are updated;
tenant copies stay frozen at the permissions they were given when the
tenant was provisioned.

### Why are the host ports different from the reference stack?

The reference backend's compose file uses ports 5432 / 6379 / 8000 / 3000.
This project deliberately ships on **5433 / 6380 / 8001 / 3001** so the two
stacks can run on the same machine without colliding. Container names are also
prefixed with `bunchly_` so `docker ps` is unambiguous.

---

## Local development (without Docker)

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -r requirements/dev.txt
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py migrate
python manage.py bootstrap_demo
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev          # serves on http://localhost:5173 with /api proxied to :8000
```

---

## Architecture highlights

- **Multi-tenant from day one.** Every tenant-owned table includes
  `tenant_id`, queries filter through `TenantModelViewSet`, and the
  JWT carries the active tenant claim.
- **JWT auth + RBAC.** Login returns access/refresh + a list of tenant
  memberships. The frontend reads `/api/v1/auth/me/` to get the current
  user's permission codes and gates the sidebar + routes against them.
  There is **no client-side role switcher** — different "views" come
  from different user accounts, exactly like the backend's RBAC intends.
- **Tenant switcher (real).** Users with multiple memberships see a tenant
  selector in the topbar that calls `/auth/switch-tenant/` to swap the
  bound JWT.
- **Configurable workflow & notification engine** (Celery Beat-driven).
- **Contract generation.** The backend renders tenant-branded DOCX
  contracts from `EmploymentContract` records — the Employee detail page
  surfaces this via a **Generate DOCX** action that streams the file
  back to the browser.
- **Stateless backend, horizontally scalable** behind Gunicorn.
- **Light + dark mode**, persisted to localStorage and honouring the
  user's system preference.

---

## Status / roadmap

See [`handoff.md`](./handoff.md) for the authoritative "what's done /
what's next" state. Short version:

| Area                              | State              |
| --------------------------------- | ------------------ |
| Backend (all 25+ modules)         | Working from reference copy |
| Frontend shell, auth, RBAC        | Done               |
| Dashboard, People, Employee detail | Wired to API       |
| Contract DOCX generation          | Wired to API       |
| Leave / Documents / Education     | List views wired; action UIs pending |
| Recruitment / Onboarding / Payroll / Performance / Learning / HR Cases / Assets / Imports / Reports / Audit / Settings | Coming-soon shells in the UI, backend endpoints exist |
| Docker Compose (this stack)       | Done               |

---

## Reading list before the next session

1. `handoff.md` — start here. Always.
2. `bunchly-build-prompt.md` — the original spec, single source of truth.
3. `Bunchly frontend redesign/` — the prototype kept for visual reference.

# MazadJo — frontend integration hub

This folder holds **per-component handoff guides** for the web app. Start here (Phase 0), then follow phases in order.

| Phase | Doc | Status |
|-------|-----|--------|
| 0 | This README | Ready |
| 1 | [01-identity-and-auth.md](01-identity-and-auth.md) | Ready |
| 1b | [01b-kyc.md](01b-kyc.md) | Deferred |
| 2 | [02-reference-catalog.md](02-reference-catalog.md) | Ready |
| 3 | [03-listings-and-media.md](03-listings-and-media.md) | Ready |
| 3 (CMS) | [03-cms-and-configuration.md](03-cms-and-configuration.md) | Ready |
| 4 | [04-auction-lifecycle.md](04-auction-lifecycle.md) | Ready |
| 5 | [05-subscriptions-and-payments.md](05-subscriptions-and-payments.md) | Ready |
| 6 | [06-live-bidding-realtime.md](06-live-bidding-realtime.md) | Planned |
| 7 | [07-post-auction-settlement.md](07-post-auction-settlement.md) | Planned |
| 8 | [08-trust-and-operations.md](08-trust-and-operations.md) | Planned |

**Master HTTP reference:** [../API.md](../API.md)  
**Architecture index:** [../SYSTEM_DESIGN.md](../SYSTEM_DESIGN.md)  
**ER / system diagrams:** [../er-diagram.mmd](../er-diagram.mmd), [../system-structure.mmd](../system-structure.mmd)

---

## Phase 0 — local API bootstrap

Goal: run the backend, open Swagger, and call `/api/v1/` from a web app (directly or via dev proxy).

### Prerequisites

- Python 3.11+ (see project `pyproject.toml`)
- Optional: PostgreSQL, Redis (recommended for WebSocket + Celery outside eager mode)

### 1. Virtualenv and dependencies

```bash
cd /path/to/MazadJo_Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment file

Copy the template and edit:

```bash
cp .env.example .env
```

**Minimum checklist for web + auction dev:**

| Variable | Purpose | Local suggestion |
|----------|---------|------------------|
| `SECRET_KEY` | Django signing | Any non-empty string when `DEBUG=True` |
| `DEBUG` | Dev mode | `True` |
| `ALLOWED_HOSTS` | HTTP host header | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Browser calls API from web origin | `http://localhost:3000,http://localhost:3001` (public + staff Next apps) |
| `FIXED_OTP` | Skip real SMS/email in dev | `True` → OTP code is always `1111` |
| `WEBHOOK_PAYMENT_SECRET` | HMAC for `POST /webhooks/payments/` | Any shared secret string for local tests |
| `REDIS_URL` | Channels + Celery broker | `redis://127.0.0.1:6379/0` when testing WS or async workers |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | Token lifetime | Defaults in `.env.example` are fine |

**Database:** leave `POSTGRES_DB` and `DATABASE_URL` empty to use SQLite (`db.sqlite3`). Use Postgres in `.env` when you need production-like DB behavior.

**Celery without Redis:** if `REDIS_URL` and `CELERY_BROKER_URL` are unset, tasks run **eagerly** in-process (fine for auth/CRUD; WebSocket still needs Redis for multi-process).

### 3. Database and periodic tasks

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_celery_beat
.venv/bin/python manage.py seed_catalog
```

`seed_celery_beat` is idempotent — it registers OTP cleanup, notification email sweep, auction close sweep, and fraud score decay in **django-celery-beat**.

`seed_catalog` is idempotent — Jordan (`JO`), sample cities/areas, and four product categories with `ProductSettings`.

### 4. Optional demo data

```bash
# Category + demo seller + two ACTIVE auctions (for bidding UI smoke tests)
.venv/bin/python manage.py seed_demo_auctions
```

- Seller username: `demo_seller`  
- Password (if newly created): `demo-seller-pass-99`  

Requires `seed_catalog` (or Django admin) before creating auctions with real categories. `seed_demo_auctions` still adds its own “Demo category” if you skip the full catalog seed.

### 5. Run the server

**HTTP only (no WebSocket):**

```bash
.venv/bin/python manage.py runserver
```

**HTTP + WebSocket (recommended for live bidding):**

```bash
# Requires REDIS_URL
.venv/bin/python -m daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

**Celery (optional — OTP email, close sweep, webhooks):**

```bash
celery -A core worker -l info
celery -A core beat -l info   # uses DB scheduler after seed_celery_beat
```

### 6. Verify the API

| Check | URL |
|-------|-----|
| OpenAPI schema | http://127.0.0.1:8000/api/schema/ |
| Swagger UI | http://127.0.0.1:8000/api/schema/swagger-ui/ |
| Health (categories) | http://127.0.0.1:8000/api/v1/categories/ |
| Register + token | See [../API.md](../API.md#auth-and-users) |

Quick auth smoke test:

```bash
# Register
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/register/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"dev1","password":"dev-pass-99"}'

# Token
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"dev1","password":"dev-pass-99"}'
```

Automated regression (backend):

```bash
./docs/run_api_tests.sh
```

---

## Web app — API base URL and CORS

**API base:** `http://127.0.0.1:8000/api/v1/`  
**Auth header:** `Authorization: Bearer <access_token>`

Set `CORS_ALLOWED_ORIGINS` to your frontend origins (e.g. `http://localhost:3000,http://localhost:3001` for the public and staff Next.js apps). With `DEBUG=True` and empty origins, CORS may allow all origins — still set explicit origins before staging.

### Dev proxy (avoid CORS during local UI work)

Point the frontend dev server at the API so the browser sees same-origin requests.

**Vite (`vite.config.ts`):**

```ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
```

Then use base URL `/api/v1/` in the client (relative to the dev server).

**Next.js (`next.config.js`):**

```js
async rewrites() {
  return [
    { source: '/api/:path*', destination: 'http://127.0.0.1:8000/api/:path*' },
  ];
},
```

**WebSocket:** proxy `/ws` to `ws://127.0.0.1:8000` in Vite, or connect directly to `ws://127.0.0.1:8000/ws/auctions/<id>/?token=<access>` when CORS is not involved.

---

## Locked MVP decisions (integration roadmap)

| Topic | Decision |
|-------|----------|
| Identity | OTP phone/email; KYC deferred (Phase 1b) |
| Media | Binary in DB + dedicated serve URLs (Phase 3) |
| Client | Web app first |
| Payments | Staging-only: `mark_paid` + test webhook (Phase 5) |

---

## Phase checklist (frontend team)

- [ ] `.env` created from `.env.example`
- [ ] `migrate` + `seed_celery_beat` succeed
- [ ] Swagger UI loads at `/api/schema/swagger-ui/`
- [ ] `CORS_ALLOWED_ORIGINS` matches web dev URL (or proxy configured)
- [ ] Register + JWT token + `GET /api/v1/users/me/` work
- [ ] `seed_catalog` → `GET /api/v1/categories/` returns categories with `settings`
- [ ] (Optional) `seed_demo_auctions` + login as `demo_seller`
- [ ] (Optional) Redis + Daphne for WebSocket bidding tests

Next: **[Phase 5 — Subscriptions and payments](05-subscriptions-and-payments.md)** (complete). Then **Phase 6 — Live bidding**.

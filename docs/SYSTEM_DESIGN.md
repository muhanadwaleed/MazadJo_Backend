# MazadJo — system design (index)

High-level backend architecture for MazadJo. Detailed **frontend handoff** lives under [integrations/](integrations/README.md).

## Core invariants

- **One auction entity** — pre-publish and live bidding share the `Auction` model; status drives the phase (no parallel “request” table).
- **Subscribe before bid** — active `AuctionSubscription` required inside the bid transaction.
- **Server-side bidding rules** — min increment, timing, anti-sniping, and close logic run in [`bidding/services.py`](../bidding/services.py).
- **Payments** — provider-agnostic `PaymentTransaction` + HMAC webhook; MVP uses staging activation (`mark_paid` / test webhook).
- **Privacy** — masked bidder identity on public bid feeds and WebSocket during live auctions.

## Diagrams

| Artifact | Description |
|----------|-------------|
| [er-diagram.mmd](er-diagram.mmd) | Entity relationships |
| [system-structure.mmd](system-structure.mmd) | Apps, services, and flows |

## HTTP routing

| Layer | Module |
|-------|--------|
| Project | `core/urls.py` → `api/v1/` → `core/api_v1_urls.py` |
| Per app | `accounts/urls.py`, `catalog/urls.py`, `cms/urls.py`, `configuration/urls.py`, `auctions/urls.py`, `subscriptions/urls.py`, `payments/urls.py`, `notifications/urls.py`, `ratings/urls.py`, `audit/urls.py` |

`bidding` has no `urls.py` — bid routes are actions on `AuctionViewSet` in `auctions/urls.py`.

## HTTP and realtime

| Surface | Entry |
|---------|--------|
| REST v1 | `/api/v1/` — see [API.md](API.md) |
| OpenAPI | `/api/schema/`, `/api/schema/swagger-ui/` |
| WebSocket | `ws://<host>/ws/auctions/<auction_id>/?token=<JWT>` |

## Django apps (domain map)

| App | Responsibility |
|-----|----------------|
| `accounts` | Users, OTP, JWT-facing profile |
| `catalog` | Geo, categories, `ProductSettings` |
| `cms` | FAQ, who/why us, contact content |
| `configuration` | Fees per category, terms, review checklist templates & per-auction snapshots |
| `auctions` | Listings, lifecycle, watchlist, WS consumer |
| `bidding` | Bids, idempotency, anti-snipe |
| `subscriptions` | Auction entry fees |
| `payments` | Transactions, webhooks |
| `notifications` | In-app + email queue |
| `ratings` | Ratings, disputes, alerts |
| `audit` | Staff audit log |
| `fraud` | Risk scoring (async) |
| `core` | Django project package (settings, URLs, Celery, ASGI, shared DRF helpers) |

## Integration phases

Follow [integrations/README.md](integrations/README.md) for phased frontend delivery (0 → 8).

## Background jobs

After `migrate`, run `python manage.py seed_celery_beat` and `python manage.py seed_catalog` (Jordan geo + sample categories). Periodic tasks include OTP cleanup, notification email processing, auction close sweep, and fraud score decay. See [API.md](API.md) methodology section.

## Observability

- Structured loggers: `mazadjo.bids`, `mazadjo.otp`, `mazadjo.fraud`
- Optional Prometheus: `GET /metrics/` when `ENABLE_PROMETHEUS_METRICS=True`
- Optional Sentry: `SENTRY_DSN`

---

*This document grows as each integration phase ships; avoid duplicating endpoint contracts here — link to [API.md](API.md) instead.*

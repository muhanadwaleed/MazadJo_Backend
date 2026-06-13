# MazadJo HTTP API (v1)

**Frontend integration (phased handoff):** [integrations/README.md](integrations/README.md)

Base path: `/api/v1/` (JWT and domain APIs live under this prefix; older `/api/auth/token/` routes were removed.)

## Design choices (methodology)

- **Pagination**: page number with `page` / `page_size` for most list endpoints; **bid history** uses **cursor** pagination (`cursor`, `page_size`) for stable feeds under load.
- **Payment webhooks**: one generic HMAC-signed endpoint; map gateway-specific payloads in the Celery task as providers are integrated.
- **Staging payment simulation**: `POST /subscriptions/{id}/mark_paid/` lets the subscription owner mark their row paid without a real gateway (staff can still mark any subscription).
- **Celery beat**: schedules live in the database via **django-celery-beat** (`CELERY_BEAT_SCHEDULER=DatabaseScheduler`). Run `python manage.py seed_celery_beat` after migrations to create default periodic tasks (OTP cleanup, notification email sweep, auction close sweep, **fraud risk-score decay** `fraud.tasks.decay_risk_scores`, etc.).
- **Anti-sniping**: when `auction_extension_enabled`, extend if time left is within `extension_trigger_seconds` **or** under `ANTI_SNIPE_FORCE_SECONDS` (default 10s). Extension adds `extension_minutes` to `ends_at`, increments `extension_count`, and updates `extend_deadline`.
- **Auction close**: not only Celery — `maybe_close_auction` runs on **bid placement** (after locking the auction), on **GET auction detail** (`retrieve`), and via **`auctions.tasks.close_due_auctions`** (beat every ~60s after `seed_celery_beat`).
- **Bidding**: `place_bid` is one transaction: lock auction → optional close → idempotency check → abuse checks → lock subscription → (optional) anti-sniping extend → write bid / idempotency row → update price & snapshots for **public** bids → WS payload **after commit** for public bids only. Optional header **`Idempotency-Key`**: replays return the same `Bid` (no duplicate bids).
- **Rate limit**: per user per auction per second via cache (`BID_MAX_PER_SECOND_PER_USER`); over limit returns **429** (`Throttled`).
- **Shadow / fraud bids**: when `SHADOW_BID_SILENT_PUBLICATION` is **True** (default), users who are staff-shadow-banned or (if enabled) at/above the configured risk score still receive **HTTP 201** with a normal bid payload, but the bid is stored with **`suppress_publication`** — it does **not** appear in `GET /auctions/{id}/bids/`, does **not** change `current_price`, does **not** trigger anti-sniping, WebSocket `bid_placed`, or async fraud analysis. When `SHADOW_BID_SILENT_PUBLICATION` is **False**, shadow cases return **403** instead (`PermissionDenied`).
- **Fraud scoring**: async `analyze_bid_fraud` runs after public bids (pumping window `RISK_PUMPING_WINDOW_SECONDS`, shared-IP heuristics, win-ratio using denormalized `UserStats`). Risk scores decay on the beat schedule (`RISK_DECAY_*` settings). See `.env.example` for tunables.
- **OTP**: generation and **hash-only storage** happen inside Celery `dispatch_otp_delivery` (no plaintext in the broker). **Rate limit**: `OTP_RATE_LIMIT_MAX` requests per `OTP_RATE_LIMIT_WINDOW_MINUTES` per destination+purpose. SMS uses **`SMS_HTTP_TIMEOUT`** (default 5s) and task **retries** (3×). API responds **`202 Accepted`** with approximate `expires_at`.

**Authentication:** JWT via `Authorization: Bearer <access_token>`. Obtain tokens at `POST /api/v1/auth/token/` with JSON body `{"username":"...","password":"..."}`.

**Pagination:** list endpoints use `?page=` and `?page_size=` (max 100). Response shape follows Django REST framework page-number pagination (`count`, `next`, `previous`, `results`).

## Machine-readable schema

- OpenAPI 3 schema: `GET /api/schema/`
- Swagger UI: `GET /api/schema/swagger-ui/`

## CORS

Configure `CORS_ALLOWED_ORIGINS` (comma-separated) in `.env`. When empty, `CORS_ALLOW_ALL_ORIGINS` defaults to the same value as `DEBUG` (open in local dev only).

## API governance

- **Versioning**: all stable contracts stay under `/api/v1/`. Breaking changes require a new major path (for example `/api/v2/`).
- **Deprecation**: deprecate endpoints/fields with a documented notice window before removal, and document migration path in release notes.
- **Backward compatibility**: additive changes are preferred within the same major version; avoid changing semantic meaning of existing fields.
- **Idempotent write safety**: clients should send `Idempotency-Key` for retry-prone writes (`POST /auctions/{id}/bids/`, webhook-driven financial state changes, refund workflows).
- **Traceability**: clients may send `X-Request-ID`; server-generated correlation IDs must be echoed/logged when absent.

### Standard error envelope

When an endpoint returns errors, preserve HTTP status code and prefer this envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human readable summary",
    "details": {
      "field": [
        "Specific validation error"
      ]
    },
    "request_id": "req_123"
  }
}
```

Notes:
- `code` is stable for machines; `message` is for operators/users.
- `details` is optional and can carry field or domain-specific errors.
- `request_id` enables support/debug correlation across API, worker, and audit logs.

## Auth and users

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register/` | Public | Create user (`username`, `password`, optional profile fields). |
| POST | `/auth/token/` | Public | JWT access + refresh. |
| POST | `/auth/token/refresh/` | Public | Refresh access token. |
| POST | `/auth/token/verify/` | Public | Verify token. |
| POST | `/auth/otp/request/` | Mixed | **`202`** — queues `dispatch_otp_delivery` (hashed OTP in DB only). Rate-limited (`OTP_RATE_LIMIT_*`). Email / SMS with retries + SMS timeout. |
| POST | `/auth/otp/verify/` | Public | Verify OTP code. For `purpose=register`, sets pre-signup verification (see register rules). |
| POST | `/auth/otp/verification-status/` | Public | Body: destination + `purpose=register` → `{ verified, verified_at }`. |
| POST | `/auth/password/reset/request/` | Public | Queue password-reset OTP (`login_reset`) for matching email/phone. **`202`** always when account unknown; **`403`** `account_disabled` if account blocked. |
| POST | `/auth/password/reset/confirm/` | Public | Body: destination + `code` + `new_password`. **`200`** on success; **`400`** `invalid_otp` if code wrong. |
| GET/PUT/PATCH | `/users/me/` | User | Current user profile. |

**Blocked / inactive accounts:** `is_blocked` or `is_active=false` users cannot obtain JWTs, refresh tokens, or use Bearer auth (`error.code` = `account_disabled`).

### Auth request/response contracts (exact)

#### `POST /auth/register/`

Request JSON:

```json
{
  "username": "u1",
  "password": "complex-pass-99",
  "email": "u1@example.com",
  "full_name_ar": "",
  "full_name_en": "User One",
  "phone_number": "790000000",
  "country_code": "+962"
}
```

Rules:
- Required: `username`, `password` (min length 8; not too similar to profile fields; not entirely numeric). Common-password blocklist is **disabled** for easier dev/staging.
- Optional: `email`, `full_name_ar`, `full_name_en`, `phone_number`, `country_code`.
- If `phone_number` is sent, it must match a **verified** register OTP for that phone (within `REGISTRATION_OTP_MAX_AGE_MINUTES`, default 30). Same for `email` when provided.
- Flow: `POST /auth/otp/request/` + `POST /auth/otp/verify/` with `purpose=register` for each destination **before** register.

Response `201` returns user profile object (without password). `is_phone_verified` / `is_email_verified` are set when the matching pre-register OTP was verified.

#### `POST /auth/otp/request/`

Request JSON:

```json
{
  "destination_type": "phone",
  "destination_value": "790000000",
  "purpose": "register"
}
```

Allowed values:
- `destination_type`: `phone` | `email`
- `purpose`: `register` | `login_reset` | `verify_phone` | `verify_email`

Auth behavior:
- Public calls are allowed only when `purpose=register`.
- For other purposes, caller must be authenticated (JWT) or API returns `401`.

Success response is `202`:

```json
{
  "detail": "OTP queued for delivery.",
  "expires_in_minutes": 10,
  "expires_at": "2026-04-16T18:00:00Z"
}
```

#### `POST /auth/otp/verify/`

Request JSON:

```json
{
  "destination_type": "phone",
  "destination_value": "790000000",
  "purpose": "register",
  "code": "1111"
}
```

Important:
- `destination_type`, `destination_value`, and `purpose` must match the exact values used in `/auth/otp/request/`.
- `code` is max length 8.
- If `FIXED_OTP=True` in environment, verification code is always `1111`.

Responses:
- `200`: `{"detail":"Verified."}`
- `400`: invalid OTP (`error.code` = `invalid_otp`) or field validation errors.

#### `POST /auth/password/reset/request/`

Request JSON (same shape as OTP destination):

```json
{
  "destination_type": "email",
  "destination_value": "user@example.com"
}
```

Response **`202`**:

```json
{
  "detail": "If an account exists for this destination, a reset code was queued.",
  "expires_in_minutes": 10,
  "expires_at": "2026-04-16T18:00:00Z"
}
```

#### `POST /auth/password/reset/confirm/`

```json
{
  "destination_type": "email",
  "destination_value": "user@example.com",
  "code": "1111",
  "new_password": "new-complex-pass-99"
}
```

Response **`200`**: `{"detail":"Password updated."}`

## Catalog

Public reference data for location pickers and category-driven listing rules. Seed local data: `python manage.py seed_catalog` (Jordan geo + sample categories). Handoff: [integrations/02-reference-catalog.md](integrations/02-reference-catalog.md).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/countries/` | Public | Active countries only (`name_ar`, `name_en`, `code`). Staff GET lists inactive too. |
| POST/PATCH/DELETE | `/countries/{id}/` | Staff | Manage countries. |
| GET | `/cities/?country=<id>` | Public | Active cities; filter by country id. Staff GET lists inactive too. |
| POST/PATCH/DELETE | `/cities/{id}/` | Staff | Manage cities. |
| GET | `/areas/?city=<id>` | Public | Active areas; filter by city id. Staff GET lists inactive too. |
| POST/PATCH/DELETE | `/areas/{id}/` | Staff | Manage areas. |
| GET | `/categories/` | Public | Active product categories with nested **`settings`** and read-only **`fees`**. Staff GET lists inactive too. |
| POST/PATCH/DELETE | `/categories/{id}/` | Staff | Manage categories; POST/PATCH accepts nested **`settings`**. |

**Auction create:** `product_category` must have a related `ProductSettings` row; otherwise **400** with `product_category`: `"Category has no product settings."`

**`settings` fields** (when present): `min_images_count`, `max_images_count`, `video_allowed`, `max_video_duration_sec`, `attachments_allowed`, `allowed_extensions_json`, `location_link_enabled`, `min_start_price`, `min_bid_increment`, `reserve_price_required`, `inspection_required`, `blur_option_enabled`, `delivery_period_days`, `auction_extension_enabled`, `extension_minutes`, `extension_trigger_seconds`, `is_active`.

**`fees` fields** (read-only on category): `bidder_insurance_amount`, `seller_insurance_amount`, `subscription_amount` (used when creating `AuctionSubscription`).

## CMS

Public reads return **active** rows only; staff can create/update/delete. Handoff: [integrations/03-cms-and-configuration.md](integrations/03-cms-and-configuration.md).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/faqs/` | Public | Active FAQs ordered by `sort_order`. |
| POST/PATCH/DELETE | `/faqs/{id}/` | Staff | Manage FAQs. |
| GET | `/who-us/` | Public | Active “who us” sections. |
| POST/PATCH/DELETE | `/who-us/{id}/` | Staff | Manage sections. |
| GET | `/why-us/` | Public | Active “why us” sections. |
| POST/PATCH/DELETE | `/why-us/{id}/` | Staff | Manage sections. |
| GET | `/contact-us/` | Public | Active contact rows (list). |
| GET | `/contact-us/active/` | Public | Single active contact block (404 if none). |
| POST/PATCH/DELETE | `/contact-us/{id}/` | Staff | Manage contact entries. |

## Configuration

Fees, terms, and staff review checklist templates. Handoff: [integrations/03-cms-and-configuration.md](integrations/03-cms-and-configuration.md).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/fees-configurations/` | Public | List fee groups. |
| POST/PATCH/DELETE | `/fees-configurations/{id}/` | Staff | Manage fee groups (each group must keep ≥1 category). |
| GET | `/checklist-items/` | Public | Active checklist template items. |
| POST/PATCH/DELETE | `/checklist-items/{id}/` | Staff | Manage template items. |
| PUT | `/categories/{id}/checklist-items/` | Staff | Body: `{"checklist_item_ids": [1,2,...]}` — assign checklist to a product category. |
| GET | `/categories/{id}/checklist-items/` | Staff | Current checklist assignment for a category. |
| GET | `/terms/` | Public | Active terms versions only (staff sees all via authenticated staff session). |
| GET | `/terms/active/` | Public | Current active terms document. |
| POST/PATCH/DELETE | `/terms/{id}/` | Staff | Manage terms; only one `is_active=true` at a time. |

## Auctions and bids

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/auctions/` | Public | List; filters: `status`, `category`, `area`, `search` (title + description). Default list shows **public browse statuses** only (`scheduled`, `active`, `ended`, …). **`status`** for pre-publish states (`draft`, `under_review`, `approved`, …) is **staff-only** (others get an empty list). **`mine=1`**: authenticated seller’s auctions (any status). **`seller=<user_id>`**: staff only. List rows include **`primary_media_url`** (first image serve URL or `null`). |
| POST | `/auctions/` | User | Create **draft** auction (seller). Body: `product_category`, `title`, `description`, `area`, `location_link`, `start_price`, `reserve_price`, `min_bid_increment`, **`duration_days`**, `is_anonymous_bidding`. Server sets `auction_number`, `current_price=start_price`, `status=draft`. **`starts_at` / `ends_at`** are null until seller payment activates the listing. **`min_bid_increment`** defaults from category `settings` when omitted. |
| GET | `/auctions/{id}/` | Public | Detail with **`media_items`** metadata (`url` only — no `file_data`). Increments **`views_count`**. Triggers **close-if-past-end** before response. |
| PUT/PATCH | `/auctions/{id}/` | Owner | Update auction only in `draft` or `returned_for_edit`. Category settings validated on save. |
| POST | `/auctions/{id}/media/` | Owner | **Multipart** upload: `file`, `media_type` (`image` \| `video` \| `file`), optional `sort_order`, `is_blurred`. Owner only in `draft` / `returned_for_edit`. Max size **`AUCTION_MEDIA_MAX_BYTES`** (default 10 MB). Returns metadata + **`url`** serve path. |
| GET | `/auctions/{id}/media/{media_id}/` | Public / owner | Binary body with `Content-Type`. Public when auction is browseable; owner/staff for pre-publish drafts. |
| DELETE | `/auctions/{id}/media/{media_id}/` | Owner | Remove media; owner only in `draft` / `returned_for_edit`. |
| POST | `/auctions/{id}/submit/` | Owner | Move auction from `draft`/`returned_for_edit` to `under_review`. Validates fields + **`min_images_count`** (and related media rules) before transition. Snapshots category review checklist onto the auction. |
| GET/PATCH | `/auctions/{id}/review-checklist/` | Staff | List per-auction checklist rows (from configuration templates); PATCH body: `{"id": <row_id>, "is_checked": true\|false}`. |
| POST | `/auctions/{id}/staff/review/` | Staff | Body: `decision` (`approve` / `reject` / `return_for_edit`), optional `reason`. Auction must be `under_review`. **`approve`** requires all checklist rows checked. Writes audit log. |
| POST | `/auctions/{id}/cancel/` | Owner | **Seller only** (not staff). Cancels in `draft`, `returned_for_edit`, `under_review`, `approved`, or `scheduled`. Optional body: `reason`. Writes audit log. |
| POST/DELETE | `/auctions/{id}/watchlist/` | User | Add or remove watchlist entry. |
| GET | `/auctions/{id}/bids/` | Public | Bid history (**public bids only**; suppressed shadow bids are omitted): **cursor** pagination (`cursor`, `page_size`). Optional **`since`** (ISO 8601) for polling — only bids with `created_at` greater than `since`. List fields: **`id`**, **`amount`**, masked **`bidder`**, **`timestamp`**. |
| POST | `/auctions/{id}/bids/` | User | Place bid. Requires **active** subscription for this auction. Without it: **403** `subscription_required`. Header **`Idempotency-Key`** optional. Body: `amount`, **`bid_source`** (`manual` \| `quick_increment`, default `manual`). |

## Real-time (WebSocket)

Connect (after ASGI + Channels, Redis recommended for multi-worker):

`GET ws(s)://<host>/ws/auctions/<auction_id>/?token=<JWT_access_token>`

Connection requires a valid JWT and the auction must exist and not be **cancelled**. Payload shape after a **public** bid (after DB commit):  
`{"type":"bid_placed","auction_id", "bid_id", "current_price", "bidder":"ab***", "ends_at":"...", "extension_applied":bool}`. **Suppressed** (shadow) bids do not emit this event. Use **GET `/auctions/{id}/bids/`** as the HTTP fallback when the socket is down.

## Observability

- **Logs**: structured loggers `mazadjo.bids`, `mazadjo.otp`, `mazadjo.fraud` (see `DJANGO_LOG_LEVEL` in `.env`).
- **Prometheus** (when `ENABLE_PROMETHEUS_METRICS=True`): scrape **`GET /metrics/`** (optional header `X-Metrics-Token` if `METRICS_SCRAPE_TOKEN` is set). Includes bid counters, OTP counters, WebSocket gauge, and fraud series such as `mazadjo_fraud_score_distribution`, `mazadjo_fraud_flags_total{flag_type=...}`, `mazadjo_fraud_feedback_total{outcome=...}` (for human review labels from tooling).
- **Sentry**: optional `SENTRY_DSN` (initialized from the `observability` app when set).

## Subscriptions

**Staging-only payments** — no gateway checkout in MVP. Handoff: [integrations/05-subscriptions-and-payments.md](integrations/05-subscriptions-and-payments.md).

Fees from `auction.product_category.fees_configuration`: **seller** pays `seller_insurance_amount + subscription_amount` when `approved`; **bidder** pays `bidder_insurance_amount + subscription_amount` when auction is `active`. No `role` field — inferred from `auction.seller_id`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/subscriptions/` | User | List own (staff: all). Filters: `?auction=<id>`, `?status=`. |
| POST | `/subscriptions/` | User | Body: `{"auction": <id>}`. Optional **`Idempotency-Key`**. Returns `insurance_fee`, `subscription_fee`, `total_fee`, `participant_type`, nested `payment_transaction`. Seller payment (when activated) sets auction `active` and `ends_at = paid_at + duration_days`. |
| POST | `/subscriptions/{id}/mark_paid/` | User (own subscription; staff: any) | Staging simulation: mark paid; activates subscription; seller payment also activates auction. Idempotent if already `active`. |

## Payments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/payments/transactions/` | User | Own transactions (staff: all). Filter: `?auction=<id>`. |

### Payment webhook (Celery)

`POST /api/v1/webhooks/payments/` — no JWT. Header `X-Webhook-Signature: sha256=<hex>` where `<hex>` is HMAC-SHA256 of the raw request body using `WEBHOOK_PAYMENT_SECRET`. JSON body must include `provider_reference` (matches `PaymentTransaction.provider_reference`) and `status` (`succeeded`, `failed`, etc.). Returns `202` and processes asynchronously via `payments.tasks.apply_payment_webhook_payload`.

## Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/notifications/` | User | List notifications. |
| PATCH | `/notifications/{id}/read/` | User | Mark as read. |

Email delivery for pending rows is queued by a periodic task (`notifications.tasks.process_pending_email_notifications`) defined in django-celery-beat after `seed_celery_beat`.

## Ratings and disputes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/ratings/options/` | Public | Active rating issue options. |
| GET/POST | `/ratings/` | User | List (optional `?auction=`); create rating. |
| POST | `/rating-issue-reports/` | User | Report an issue on a rating. |
| GET/POST | `/disputes/` | User | List/create disputes for involved parties. |

## Audit

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/audit-logs/` | Staff | Audit log entries (paginated). |

## Data retention and privacy governance

- Keep audit and payment records according to legal/compliance windows; avoid indefinite retention without policy.
- Define retention windows per class:
  - security/audit trails
  - payment transaction metadata
  - media and document objects
  - OTP verification records
- Use soft-delete or archival for business entities where legal traceability is required.
- For expired or unnecessary PII, apply anonymization/pseudonymization workflows where allowed.
- Never expose private participant identities during active auctions; enforce role-based response shaping server-side.

## Automated API tests

From the project root:

```bash
.venv/bin/python manage.py test accounts.tests.test_api_integration accounts.tests.test_auth_phase1 auctions.test_draft_list_api auctions.test_media_api auctions.test_lifecycle_api auctions.test_watchlist_api subscriptions.tests bidding.tests -v2
```

Or run `docs/run_api_tests.sh`.

With **pytest** (after `pip install -r requirements.txt`):

```bash
DJANGO_SETTINGS_MODULE=core.settings .venv/bin/python -m pytest accounts/tests auctions/test_draft_list_api.py auctions/test_media_api.py auctions/test_lifecycle_api.py auctions/test_watchlist_api.py subscriptions/tests bidding/tests -q
```

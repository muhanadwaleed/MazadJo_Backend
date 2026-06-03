# Phase 2 — Reference catalog (web)

Handoff guide for country → city → area pickers and category selection with rule preview. Contract details: [API.md](../API.md#catalog-read-only).

**Prerequisites:** [README.md](README.md) (Phase 0), [01-identity-and-auth.md](01-identity-and-auth.md) (JWT for seller flows that consume catalog after login).

---

## Screens covered

| Screen | APIs |
|--------|------|
| Location picker (country → city → area) | `GET /countries/` → `GET /cities/?country=` → `GET /areas/?city=` |
| Category picker + rule preview | `GET /categories/` (nested `settings`) |
| Seller listing wizard (category step) | Same; store `product_category` id + cache `settings` for later steps |
| Staff ops | `GET/POST/PATCH/DELETE` on `/countries/`, `/cities/`, `/areas/`, `/categories/` (staff JWT) |

**Staff REST CRUD** is available for geo and categories (including nested `settings` on create/update). Public clients remain read-only.

---

## Auth matrix

| Endpoint | Auth |
|----------|------|
| `GET /countries/` | Public |
| `GET /cities/?country=<id>` | Public |
| `GET /areas/?city=<id>` | Public |
| `GET /categories/` | Public |
| Django admin catalog models | Staff (`is_staff=True`) — optional alternative |
| `POST/PATCH/DELETE /countries/`, `/cities/`, `/areas/`, `/categories/` | Staff JWT |

---

## Endpoints

Base: `/api/v1/`. All catalog routes are **read-only** (`GET` list + detail).

| Method | Path | Notes |
|--------|------|--------|
| GET | `/countries/` | Active countries only |
| GET | `/cities/?country=<id>` | Optional filter by country |
| GET | `/areas/?city=<id>` | Optional filter by city |
| GET | `/categories/` | Active categories; each row includes nested `settings` when configured |

List responses use standard pagination (`count`, `next`, `previous`, `results`).

### Bilingual fields

Each geo row and category exposes **`name_ar`** and **`name_en`**. Pick display text from the user locale; send **numeric ids** (`country`, `city`, `area`, `product_category`) on auction create/update.

### Example `GET /categories/` (truncated)

After `python manage.py seed_catalog`:

```json
{
  "count": 4,
  "results": [
    {
      "id": 2,
      "name_ar": "إلكترونيات",
      "name_en": "Electronics",
      "category_type": "electronics",
      "requires_review": true,
      "requires_transfer_process": false,
      "requires_inspection": false,
      "is_active": true,
      "settings": {
        "min_images_count": 3,
        "max_images_count": 12,
        "video_allowed": true,
        "max_video_duration_sec": 120,
        "attachments_allowed": false,
        "allowed_extensions_json": ["jpg", "jpeg", "png", "webp", "mp4"],
        "location_link_enabled": false,
        "min_start_price": "5.00",
        "min_bid_increment": "5.00",
        "reserve_price_required": false,
        "inspection_required": false,
        "blur_option_enabled": false,
        "delivery_period_days": 5,
        "auction_extension_enabled": true,
        "extension_minutes": 5,
        "extension_trigger_seconds": 90,
        "is_active": true
      },
      "fees": {
        "bidder_insurance_amount": "2.00",
        "seller_insurance_amount": "5.00",
        "subscription_amount": "5.00"
      }
    }
  ]
}
```

Categories **without** a `ProductSettings` row are omitted from usable auction create: `POST /auctions/` returns **400** with `error.details.product_category`: `"Category has no product settings."`

---

## `ProductSettings` field reference (UI builders)

Use nested `settings` on the selected category to drive the listing wizard; use nested **`fees`** for insurance/subscription amounts and live-room hints.

| Field | Type | Frontend use |
|-------|------|----------------|
| `min_images_count` | int | Minimum photos before submit (**enforced on submit**) |
| `max_images_count` | int | Upload cap in wizard |
| `video_allowed` | bool | Show/hide video upload |
| `max_video_duration_sec` | int \| null | Max length when video allowed |
| `attachments_allowed` | bool | Extra file attachments (e.g. PDF) |
| `allowed_extensions_json` | string[] | Client-side accept list + validation messaging |
| `location_link_enabled` | bool | Show map/link field on listing |
| `min_start_price` | decimal | Floor for opening price |
| `min_bid_increment` | decimal | Default/suggested bid step (server still validates on bid) |
| `reserve_price_required` | bool | Require `reserve_price` on listing |
| `inspection_required` | bool | Show inspection disclaimer / staff checklist |
| `blur_option_enabled` | bool | Allow blurred media option (**enforced on upload**) |
| `delivery_period_days` | int | Post-sale delivery expectation copy |
| `auction_extension_enabled` | bool | Whether anti-sniping applies |
| `extension_minutes` | int | Minutes added per extension |
| `extension_trigger_seconds` | int | Bid inside this window before `ends_at` triggers extension |
| `is_active` | bool | Inactive settings should not be used for new listings |

**`fees`** on the category row (read-only):

| Field | Type | Frontend use |
|-------|------|----------------|
| `bidder_insurance_amount` | decimal | Bidder deposit / insurance copy |
| `seller_insurance_amount` | decimal | Seller deposit / insurance copy |
| `subscription_amount` | decimal | “Join auction” fee (subscriptions) |

Staff review checklist templates are configured via [03-cms-and-configuration.md](03-cms-and-configuration.md), not on `settings`.

Category-level flags on the parent row:

| Field | Meaning |
|-------|---------|
| `requires_review` | Listing goes to staff review after submit |
| `requires_transfer_process` | Show transfer/ownership steps in copy |
| `requires_inspection` | Inspection workflow expected |
| `category_type` | Stable slug for analytics/filters (`general`, `electronics`, …) |

---

## Caching strategy

- **Geo and categories change rarely** — safe to cache in memory for the session (e.g. load once after login or on app boot).
- Use **`ETag` / `Last-Modified` only if you add them later**; MVP: refetch on cold start or after admin publishes changes.
- Invalidate local cache when staff confirms catalog updates (or on daily refresh).
- Store **`product_category` id** on the draft; re-fetch category detail if user reopens wizard after a long idle period.

---

## Error codes

Catalog GET endpoints do not emit custom `error.code` values for normal use.

| Scenario | HTTP | `error.code` | Where |
|----------|------|--------------|--------|
| Invalid `country` / `city` filter | 200 | — | Empty `results` |
| Auction create with category missing settings | 400 | `validation_error` | `POST /auctions/` → `details.product_category` |

---

## Polling vs realtime

Not applicable — catalog is static HTTP. Poll only if you implement a future “catalog version” endpoint; MVP uses one-shot GET.

---

## Environment / dev shortcuts

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_catalog   # Jordan + 4 sample categories
```

| Command | Purpose |
|---------|---------|
| `seed_catalog` | Idempotent Jordan geo + categories with `ProductSettings` |
| `seed_demo_auctions` | Optional demo listings (creates its own “Demo category” if needed) |
| Django admin | Edit countries, cities, areas, categories, settings at `/admin/` |

Seeded category names (English): **General goods**, **Electronics**, **Vehicles**, **Real estate**.

---

## Acceptance checklist

```bash
.venv/bin/python manage.py test catalog.tests.test_seed_catalog -v2
```

Manual:

- [ ] `seed_catalog` → `GET /api/v1/countries/` includes Jordan (`code`: `JO`)
- [ ] `GET /api/v1/cities/?country=<jo_id>` includes Amman
- [ ] `GET /api/v1/areas/?city=<amman_id>` includes Abdoun
- [ ] `GET /api/v1/categories/` returns ≥4 categories with nested `settings`
- [ ] `POST /api/v1/auctions/` with a seeded category id succeeds (with JWT + valid body)
- [ ] Django admin: edit `FeesConfiguration` for a category and confirm next `GET /categories/` reflects `fees.subscription_amount`

---

## Open questions / deferrals

- **Enforcing `ProductSettings` on submit/review** — partial today (category must have settings on create); full media/price validation ships in **Phase 3**.
- **Multi-country expansion** — seed is Jordan-only; add countries via admin or extend `seed_catalog`.

---

## Next phase

[03-listings-and-media.md](03-listings-and-media.md) — draft wizard, media upload/serve, settings validation on create/submit.

# Phase 3 — CMS & configuration

Static/marketing content and platform configuration (fees, terms, staff review checklists).

**Prerequisites:** [Phase 0](README.md), [Phase 1](01-identity-and-auth.md), [Phase 2](02-reference-catalog.md).

**HTTP reference:** [../API.md](../API.md) — sections **CMS** and **Configuration**.

---

## CMS (public site content)

| Resource | List (public) | Staff write |
|----------|---------------|-------------|
| FAQs | `GET /api/v1/faqs/` | `POST/PATCH/DELETE /api/v1/faqs/{id}/` |
| Who us | `GET /api/v1/who-us/` | `POST/PATCH/DELETE /api/v1/who-us/{id}/` |
| Why us | `GET /api/v1/why-us/` | `POST/PATCH/DELETE /api/v1/why-us/{id}/` |
| Contact | `GET /api/v1/contact-us/active/` | `POST/PATCH/DELETE /api/v1/contact-us/{id}/` |

Public list endpoints only return rows with `is_active=true`, ordered by `sort_order`.

All CMS models use bilingual fields (`*_ar`, `*_en`).

---

## Configuration

### Fees

- Each **product category** (`GET /api/v1/categories/`) has a required `fees_configuration` (staff-managed).
- Public category payload includes read-only **`fees`**: `bidder_insurance_amount`, `seller_insurance_amount`, `subscription_amount`.
- Subscription creation uses `subscription_amount` from the category’s fee group (not `ProductSettings`).

Staff CRUD: `GET/POST/PATCH/DELETE /api/v1/fees-configurations/`. A fee group cannot exist without at least one linked category.

### Terms and conditions

- Public: `GET /api/v1/terms/active/` — current active version.
- Staff: full CRUD on `/api/v1/terms/`; activating one version deactivates others.

### Review checklist

1. Staff defines template rows: `GET/POST /api/v1/checklist-items/`.
2. Staff assigns items to a category: `PUT /api/v1/categories/{id}/checklist-items/` with `{"checklist_item_ids": [1, 2]}`.
3. When a seller submits an auction (`POST /api/v1/auctions/{id}/submit/`), checklist rows are **snapshotted** onto the auction.
4. Staff reviews via `GET/PATCH /api/v1/auctions/{id}/review-checklist/` (`is_checked`, `checked_by`, `checked_at`). **Approve** (`POST .../staff/review/`) requires all items checked.

---

## Local seed

After `migrate`:

```bash
python manage.py seed_catalog
```

Creates sample categories with fee groups and checklist assignments.

---

## Checklist for frontend

- [ ] Marketing pages load CMS endpoints (active-only).
- [ ] Listing flow shows category `fees.subscription_amount` before subscribe.
- [ ] Legal screen loads `GET /terms/active/`.
- [ ] Staff console uses configuration + review-checklist endpoints (staff JWT).

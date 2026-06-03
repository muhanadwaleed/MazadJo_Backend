---
name: live-auction-implementation
description: Implements backend changes for auction request, publish, subscription, bidding, and settlement workflows in MazadJo. Use when working on Django/DRF business logic, transaction safety, auction status transitions, or API contract updates in auction-related modules.
---

# Live Auction Implementation

## Scope

Use this skill for backend implementation tasks that touch:

- `auctions` (draft/review/publish lifecycle), `bidding`, `subscriptions`, `payments`
- service-layer business rules and status transitions
- API contract alignment in `docs/API.md`

## Workflow

1. Identify lifecycle stage touched by the change:
   - auction draft / staff review / publish (on `Auction`)
   - live bidding
   - closure and settlement
2. Confirm invariants:
   - pre-publish and live phases are distinct **statuses** on `Auction` (not a separate request entity)
   - bidding requires valid subscription state
   - auction status and min increment are enforced server-side
3. Implement in services first, then keep API views/serializers minimal.
4. For race-prone operations (especially bidding), wrap in atomic transaction and lock affected rows.
5. Queue side effects (notifications, analytics, risk checks) after successful commit.
6. Update tests and API docs if response shape, status behavior, or validation changed.

## Implementation Guardrails

- Do not trust frontend timing or price calculations.
- Avoid embedding payment provider specifics in domain services.
- Keep rejected/hidden/shadow bid behavior explicit and tested.
- Preserve auditability for staff and financial state changes.

## Validation Checklist

- [ ] Domain invariants preserved
- [ ] Concurrency-safe writes for bid-critical paths
- [ ] Permissions and role checks explicit
- [ ] Docs updated if API behavior changed
- [ ] Relevant tests added or adjusted

---
name: live-auction-realtime-qa
description: Validates realtime bidding behavior and API fallback paths for MazadJo auctions. Use when working on WebSocket events, anti-sniping extension behavior, idempotent bid submission, throttling, and bid-feed consistency.
---

# Live Auction Realtime QA

## Scope

Use this skill when validating:

- WebSocket bid event correctness
- public bid feed correctness and fallback polling
- anti-sniping extension behavior
- throttling and idempotency behavior in bid submission

## Test Workflow

1. Confirm auction is active and eligible for bidding.
2. Submit a normal bid and verify:
   - current price updates correctly
   - public bid appears in feed
   - websocket payload includes expected keys
3. Submit near auction end and verify extension behavior.
4. Re-submit same request with same idempotency key and verify no duplicate bid.
5. Trigger rapid bids and verify throttle behavior (`429` when expected).
6. Validate fallback polling with `since` returns missing events when socket is unavailable.

## Expected Behaviors

- Public bids update `current_price`, emit websocket event, and appear in public list.
- Suppressed/shadow bids must not leak into public list or realtime event stream.
- Replayed idempotent submit returns original bid identity.
- Anti-sniping extension changes `ends_at` only under configured conditions.

## Artifacts To Update

- Add or update integration tests in `bidding/tests`.
- Update `docs/API.md` if payloads, throttling behavior, or event semantics changed.

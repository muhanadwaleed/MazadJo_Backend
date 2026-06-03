"""
HTTP load test for auction bidding.

Configure via env vars; see scripts/loadtest/README.md.
"""

from __future__ import annotations

import csv
import itertools
import os
import threading
import uuid
from decimal import Decimal
from typing import Iterator

from locust import HttpUser, between, task

_DEFAULT_HOST = os.environ.get("MAZADJO_HOST", "http://127.0.0.1:8000")
AUCTION_ID = os.environ.get("MAZADJO_AUCTION_ID", "").strip()
USERS_CSV = os.environ.get("MAZADJO_USERS_CSV", "").strip()
SINGLE_USER = os.environ.get("MAZADJO_USERNAME", "").strip()
SINGLE_PASS = os.environ.get("MAZADJO_PASSWORD", "").strip()

_cred_lock = threading.Lock()
_cred_iter: Iterator[tuple[str, str]] | None = None


def _load_credentials() -> Iterator[tuple[str, str]]:
    global _cred_iter
    if _cred_iter is not None:
        return _cred_iter
    with _cred_lock:
        if _cred_iter is not None:
            return _cred_iter
        rows: list[tuple[str, str]] = []
        if USERS_CSV:
            with open(USERS_CSV, newline="", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if len(row) >= 2 and row[0].strip():
                        rows.append((row[0].strip(), row[1].strip()))
        elif SINGLE_USER and SINGLE_PASS:
            rows.append((SINGLE_USER, SINGLE_PASS))
        if not rows:
            raise RuntimeError(
                "Set MAZADJO_USERS_CSV or MAZADJO_USERNAME and MAZADJO_PASSWORD",
            )
        _cred_iter = itertools.cycle(rows)
        return _cred_iter


class AuctionBidder(HttpUser):
    host = _DEFAULT_HOST
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        if not AUCTION_ID:
            raise RuntimeError("MAZADJO_AUCTION_ID is required")
        user, password = next(_load_credentials())
        r = self.client.post(
            "/api/v1/auth/token/",
            json={"username": user, "password": password},
            name="/api/v1/auth/token/",
        )
        if r.status_code != 200:
            raise RuntimeError(
                f"Login failed for {user}: {r.status_code} {r.text[:200]}"
            )
        data = r.json()
        token = data.get("access")
        if not token:
            raise RuntimeError("No access token in response")
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(1)
    def get_auction(self) -> None:
        self.client.get(
            f"/api/v1/auctions/{AUCTION_ID}/", name="/api/v1/auctions/[id]/"
        )

    @task(5)
    def place_bid(self) -> None:
        r = self.client.get(
            f"/api/v1/auctions/{AUCTION_ID}/", name="/api/v1/auctions/[id]/"
        )
        if r.status_code != 200:
            return
        body = r.json()
        try:
            current = Decimal(str(body["current_price"]))
            inc = Decimal(str(body["min_bid_increment"]))
        except (KeyError, ValueError, TypeError):
            return
        amount = current + inc
        headers = {"Idempotency-Key": str(uuid.uuid4())}
        self.client.post(
            f"/api/v1/auctions/{AUCTION_ID}/bids/",
            json={"amount": str(amount), "bid_source": "manual"},
            headers=headers,
            name="/api/v1/auctions/[id]/bids/",
        )

# Load tests (Locust)

Install (in a virtualenv):

```bash
pip install locust
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MAZADJO_HOST` | No | Base URL, default `http://127.0.0.1:8000` |
| `MAZADJO_AUCTION_ID` | Yes | Numeric auction primary key |
| `MAZADJO_USERS_CSV` | No | Path to CSV `username,password` (one row per simulated user). If unset, `MAZADJO_USERNAME` / `MAZADJO_PASSWORD` are used for every Locust user (does not give 1000 distinct identities unless the server allows it). |

## Run (HTTP)

From the repository root:

```bash
export MAZADJO_AUCTION_ID=1
export MAZADJO_USERNAME=bidder1
export MAZADJO_PASSWORD=secret
locust -f scripts/loadtest/locustfile.py --headless -u 100 -r 10 -t 5m --host "$MAZADJO_HOST"
```

For many users, generate `users.csv` and:

```bash
export MAZADJO_USERS_CSV=/path/to/users.csv
locust -f scripts/loadtest/locustfile.py --host https://staging.example.com
```

Then open the Locust web UI (default http://127.0.0.1:8089) and ramp **users** and **spawn rate** gradually while watching Prometheus and database metrics.

## WebSockets

Locust here targets **REST** only. Add a separate WS soak test (see `docs/LOAD_TESTING.md`).

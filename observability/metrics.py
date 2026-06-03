from django.conf import settings

_bids = None
_bid_fail = None
_otp_req = None
_otp_verify = None
_ws = None
_fraud_hist = None
_fraud_flags = None
_fraud_feedback = None


def _counters():
    global _bids, _bid_fail, _otp_req, _otp_verify, _ws
    if _bids is None:
        from prometheus_client import Counter, Gauge

        _bids = Counter("mazadjo_bids_placed_total", "Accepted public bids")
        _bid_fail = Counter(
            "mazadjo_bid_rejected_total",
            "Bid attempts rejected",
            ["reason"],
        )
        _otp_req = Counter("mazadjo_otp_request_total", "OTP dispatch queued")
        _otp_verify = Counter(
            "mazadjo_otp_verify_total",
            "OTP verify outcomes",
            ["result"],
        )
        _ws = Gauge(
            "mazadjo_websocket_connections",
            "Active auction WebSocket connections",
        )
    return _bids, _bid_fail, _otp_req, _otp_verify, _ws


def _fraud_metrics():
    global _fraud_hist, _fraud_flags, _fraud_feedback
    if _fraud_hist is None:
        from prometheus_client import Counter, Histogram

        _fraud_hist = Histogram(
            "mazadjo_fraud_score_distribution",
            "Observed user risk scores after fraud processing",
            buckets=(0, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100),
        )
        _fraud_flags = Counter(
            "mazadjo_fraud_flags_total",
            "Fraud heuristics fired (for rate / dashboards)",
            ["flag_type"],
        )
        _fraud_feedback = Counter(
            "mazadjo_fraud_feedback_total",
            "Human review outcomes (Grafana: rate(false_positive)/rate(sum) as proxy for FP rate)",
            ["outcome"],
        )
    return _fraud_hist, _fraud_flags, _fraud_feedback


def metrics_enabled() -> bool:
    return bool(getattr(settings, "ENABLE_PROMETHEUS_METRICS", False))


def record_bid_placed() -> None:
    if not metrics_enabled():
        return
    _counters()[0].inc()


def record_bid_rejected(reason: str) -> None:
    if not metrics_enabled():
        return
    _counters()[1].labels(reason=reason[:60]).inc()


def record_otp_request() -> None:
    if not metrics_enabled():
        return
    _counters()[2].inc()


def record_otp_verify(*, success: bool) -> None:
    if not metrics_enabled():
        return
    _counters()[3].labels(result="ok" if success else "fail").inc()


def ws_connect() -> None:
    if not metrics_enabled():
        return
    _counters()[4].inc()


def ws_disconnect() -> None:
    if not metrics_enabled():
        return
    _counters()[4].dec()


def record_fraud_score_observed(score: int) -> None:
    if not metrics_enabled():
        return
    s = max(0.0, min(100.0, float(score)))
    _fraud_metrics()[0].observe(s)


def record_fraud_flag(flag_type: str) -> None:
    if not metrics_enabled():
        return
    _fraud_metrics()[1].labels(flag_type=flag_type[:48]).inc()


def record_fraud_human_feedback(*, outcome: str) -> None:
    """Call from admin/tools when an analyst labels a case (e.g. false_positive)."""
    if not metrics_enabled():
        return
    _fraud_metrics()[2].labels(outcome=outcome[:48]).inc()

import logging

from django.conf import settings
from django.core.cache import cache

from accounts.models import UserFingerprint

logger = logging.getLogger("mazadjo.fraud")


def _client_ip(request) -> str | None:
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip() or None
    addr = request.META.get("REMOTE_ADDR")
    return str(addr).strip() if addr else None


class FingerprintMiddleware:
    """
    Sample fingerprints for authenticated users (not every request — see cache TTL).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._maybe_record(request)
        return self.get_response(request)

    def _maybe_record(self, request) -> None:
        if not getattr(settings, "FINGERPRINT_MIDDLEWARE_ENABLED", False):
            return
        if not request.user.is_authenticated:
            return
        interval = int(getattr(settings, "FINGERPRINT_MIN_INTERVAL_SECONDS", 3600))
        if interval <= 0:
            return
        cache_key = f"fp:mid:{request.user.pk}"
        if not cache.add(cache_key, "1", timeout=interval):
            return
        ip = _client_ip(request)
        if not ip:
            logger.debug("fingerprint_skip no_ip user_id=%s", request.user.pk)
            return
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:2000]
        device_hash = (request.META.get("HTTP_X_DEVICE_HASH") or "").strip()[
            :128
        ] or None
        try:
            UserFingerprint.objects.create(
                user=request.user,
                ip_address=ip,
                user_agent=ua or None,
                device_hash=device_hash,
            )
        except Exception:
            logger.exception("fingerprint_write_failed user_id=%s", request.user.pk)

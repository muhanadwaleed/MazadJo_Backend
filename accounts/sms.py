import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone_e164: str, body: str) -> None:
    url = getattr(settings, "SMS_GATEWAY_URL", "").strip()
    if not url:
        logger.info("SMS (no SMS_GATEWAY_URL): %s — %s", phone_e164, body)
        return
    timeout = int(getattr(settings, "SMS_HTTP_TIMEOUT", 5))
    field_to = getattr(settings, "SMS_FORM_FIELD_TO", "to")
    field_msg = getattr(settings, "SMS_FORM_FIELD_MESSAGE", "message")
    data = urllib.parse.urlencode({field_to: phone_e164, field_msg: body}).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    key = getattr(settings, "SMS_GATEWAY_API_KEY", "").strip()
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status >= 400:
                logger.warning("SMS gateway HTTP %s", resp.status)
    except urllib.error.URLError as e:
        logger.warning("SMS gateway error: %s", e)
        raise

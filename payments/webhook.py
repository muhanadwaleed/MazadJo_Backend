import hashlib
import hmac
import json

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.tasks import apply_payment_webhook_payload


def verify_payment_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    secret = getattr(settings, "WEBHOOK_PAYMENT_SECRET", "") or ""
    if not secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    received = signature_header[7:]
    return hmac.compare_digest(expected, received)


class PaymentWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.body
        sig = request.META.get("HTTP_X_WEBHOOK_SIGNATURE", "")
        if not verify_payment_webhook_signature(raw, sig):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            payload = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        apply_payment_webhook_payload.delay(payload)
        return Response({"accepted": True}, status=status.HTTP_202_ACCEPTED)

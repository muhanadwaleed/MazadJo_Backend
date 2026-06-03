from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def prometheus_metrics(request):
    if not getattr(settings, "ENABLE_PROMETHEUS_METRICS", False):
        return HttpResponseForbidden("Metrics disabled.")
    token = getattr(settings, "METRICS_SCRAPE_TOKEN", "").strip()
    if token and request.headers.get("X-Metrics-Token") != token:
        return HttpResponseForbidden("Invalid metrics token.")
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)

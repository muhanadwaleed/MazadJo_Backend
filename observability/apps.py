import os

from django.apps import AppConfig


class ObservabilityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "observability"
    verbose_name = "Observability"

    def ready(self) -> None:
        dsn = os.environ.get("SENTRY_DSN", "").strip()
        if not dsn:
            return
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration

        traces = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.05"))
        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
            ],
            send_default_pii=False,
            traces_sample_rate=traces,
        )

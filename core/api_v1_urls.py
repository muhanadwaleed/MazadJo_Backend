from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("catalog.urls")),
    path("", include("auctions.urls")),
    path("", include("subscriptions.urls")),
    path("", include("payments.urls")),
    path("", include("notifications.urls")),
    path("", include("ratings.urls")),
    path("", include("audit.urls")),
    path("", include("cms.urls")),
    path("", include("configuration.urls")),
]

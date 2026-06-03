from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cms.viewsets import (
    ActiveContactUsView,
    ContactUsViewSet,
    FAQViewSet,
    WhoUsViewSet,
    WhyUsViewSet,
)

router = DefaultRouter()
router.register(r"faqs", FAQViewSet, basename="faq")
router.register(r"who-us", WhoUsViewSet, basename="who-us")
router.register(r"why-us", WhyUsViewSet, basename="why-us")
router.register(r"contact-us", ContactUsViewSet, basename="contact-us")

urlpatterns = [
    path("contact-us/active/", ActiveContactUsView.as_view(), name="contact-us-active"),
    path("", include(router.urls)),
]

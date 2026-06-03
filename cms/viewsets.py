from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from cms.models import ContactUs, FAQ, WhoUs, WhyUs
from cms.serializers import (
    ContactUsSerializer,
    FAQSerializer,
    WhoUsSerializer,
    WhyUsSerializer,
)
from core.permissions import IsStaffUser
from core.viewsets import StaffWritePublicReadMixin


class FAQViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer


class WhoUsViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = WhoUs.objects.all()
    serializer_class = WhoUsSerializer


class WhyUsViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = WhyUs.objects.all()
    serializer_class = WhyUsSerializer


class ContactUsViewSet(StaffWritePublicReadMixin, viewsets.ModelViewSet):
    queryset = ContactUs.objects.all()
    serializer_class = ContactUsSerializer


class ActiveContactUsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        contact = ContactUs.objects.filter(is_active=True).order_by("-updated_at").first()
        if contact is None:
            return Response(status=404)
        return Response(ContactUsSerializer(contact).data)

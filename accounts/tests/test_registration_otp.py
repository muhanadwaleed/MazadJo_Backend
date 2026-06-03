from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@override_settings(FIXED_OTP=True, CELERY_TASK_ALWAYS_EAGER=True)
class RegistrationOtpRequiredTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _verify_phone_for_register(self, phone: str):
        self.client.post(
            reverse("v1-otp-request"),
            {
                "destination_type": "phone",
                "destination_value": phone,
                "purpose": "register",
            },
            format="json",
        )
        return self.client.post(
            reverse("v1-otp-verify"),
            {
                "destination_type": "phone",
                "destination_value": phone,
                "purpose": "register",
                "code": "1111",
            },
            format="json",
        )

    def test_register_without_phone_verification_fails(self):
        r = self.client.post(
            reverse("v1-register"),
            {
                "username": "newuser1",
                "password": "password123",
                "phone_number": "790055566",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", r.data["error"]["details"])

    def test_register_after_phone_verification_succeeds(self):
        phone = "790055577"
        verify = self._verify_phone_for_register(phone)
        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        self.assertTrue(verify.data.get("verified_for_registration"))

        status_resp = self.client.post(
            reverse("v1-otp-verification-status"),
            {
                "destination_type": "phone",
                "destination_value": phone,
                "purpose": "register",
            },
            format="json",
        )
        self.assertTrue(status_resp.data["verified"])

        reg = self.client.post(
            reverse("v1-register"),
            {
                "username": "newuser2",
                "password": "password123",
                "phone_number": phone,
            },
            format="json",
        )
        self.assertEqual(reg.status_code, status.HTTP_201_CREATED)
        self.assertTrue(reg.data["is_phone_verified"])

    def test_register_without_phone_or_email_allowed(self):
        r = self.client.post(
            reverse("v1-register"),
            {"username": "nophone", "password": "password123"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_register_requires_email_verification_when_email_provided(self):
        email = "verifyme@example.com"
        self.client.post(
            reverse("v1-otp-request"),
            {
                "destination_type": "email",
                "destination_value": email,
                "purpose": "register",
            },
            format="json",
        )
        self.client.post(
            reverse("v1-otp-verify"),
            {
                "destination_type": "email",
                "destination_value": email,
                "purpose": "register",
                "code": "1111",
            },
            format="json",
        )
        reg = self.client.post(
            reverse("v1-register"),
            {
                "username": "emailuser",
                "password": "password123",
                "email": email,
            },
            format="json",
        )
        self.assertEqual(reg.status_code, status.HTTP_201_CREATED)
        self.assertTrue(reg.data["is_email_verified"])

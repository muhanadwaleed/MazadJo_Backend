from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@override_settings(FIXED_OTP=True, CELERY_TASK_ALWAYS_EAGER=True)
class Phase1AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_blocked_user_cannot_obtain_token(self):
        User.objects.create_user(
            username="blocked1",
            password="blocked-pass-99",
            is_blocked=True,
        )
        r = self.client.post(
            reverse("v1-token-obtain"),
            {"username": "blocked1", "password": "blocked-pass-99"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(r.data["error"]["code"], "account_disabled")

    def test_blocked_user_cannot_access_me_with_existing_token(self):
        user = User.objects.create_user(
            username="active1", password="active-pass-99"
        )
        tok = self.client.post(
            reverse("v1-token-obtain"),
            {"username": "active1", "password": "active-pass-99"},
            format="json",
        )
        access = tok.data["access"]
        user.is_blocked = True
        user.save(update_fields=["is_blocked"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = self.client.get(reverse("v1-users-me"))
        self.assertEqual(me.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(me.data["error"]["code"], "account_disabled")

    def test_register_accepts_common_password(self):
        r = self.client.post(
            reverse("v1-register"),
            {
                "username": "commonpw",
                "password": "password123",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        tok = self.client.post(
            reverse("v1-token-obtain"),
            {"username": "commonpw", "password": "password123"},
            format="json",
        )
        self.assertEqual(tok.status_code, status.HTTP_200_OK)

    def test_password_reset_flow(self):
        User.objects.create_user(
            username="resetme",
            password="old-pass-99",
            email="resetme@example.com",
        )
        req = self.client.post(
            reverse("v1-password-reset-request"),
            {
                "destination_type": "email",
                "destination_value": "resetme@example.com",
            },
            format="json",
        )
        self.assertEqual(req.status_code, status.HTTP_202_ACCEPTED)
        confirm = self.client.post(
            reverse("v1-password-reset-confirm"),
            {
                "destination_type": "email",
                "destination_value": "resetme@example.com",
                "code": "1111",
                "new_password": "new-pass-99",
            },
            format="json",
        )
        self.assertEqual(confirm.status_code, status.HTTP_200_OK)
        old_login = self.client.post(
            reverse("v1-token-obtain"),
            {"username": "resetme", "password": "old-pass-99"},
            format="json",
        )
        self.assertEqual(old_login.status_code, status.HTTP_401_UNAUTHORIZED)
        new_login = self.client.post(
            reverse("v1-token-obtain"),
            {"username": "resetme", "password": "new-pass-99"},
            format="json",
        )
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

    def test_otp_verify_phone_sets_flag(self):
        user = User.objects.create_user(
            username="phoneuser",
            password="phone-pass-99",
            phone_number="790011122",
        )
        self.client.force_authenticate(user)
        self.client.post(
            reverse("v1-otp-request"),
            {
                "destination_type": "phone",
                "destination_value": "790011122",
                "purpose": "verify_phone",
            },
            format="json",
        )
        verify = self.client.post(
            reverse("v1-otp-verify"),
            {
                "destination_type": "phone",
                "destination_value": "790011122",
                "purpose": "verify_phone",
                "code": "1111",
            },
            format="json",
        )
        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_phone_verified)

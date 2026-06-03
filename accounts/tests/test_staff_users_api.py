"""Staff user directory API tests."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class StaffUsersApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="staff1", password="staff-pass-99", is_staff=True
        )
        self.public = User.objects.create_user(
            username="seller1", password="seller-pass-99", is_staff=False
        )
        self.other_staff = User.objects.create_user(
            username="staff2",
            password="staff-pass-99",
            is_staff=True,
            user_type=User.UserType.STAFF,
        )

    def test_list_requires_staff(self):
        self.client.force_authenticate(self.public)
        r = self.client.get(reverse("staff-user-list"))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_public_users_filter(self):
        self.client.force_authenticate(self.staff)
        r = self.client.get(reverse("staff-user-list"), {"is_staff": "0"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in r.data["results"]}
        self.assertIn(self.public.id, ids)
        self.assertNotIn(self.staff.id, ids)

    def test_list_staff_users_filter(self):
        self.client.force_authenticate(self.staff)
        r = self.client.get(reverse("staff-user-list"), {"is_staff": "1"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in r.data["results"]}
        self.assertIn(self.staff.id, ids)
        self.assertNotIn(self.public.id, ids)

    def test_retrieve_user(self):
        self.client.force_authenticate(self.staff)
        r = self.client.get(reverse("staff-user-detail", args=[self.public.id]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["username"], "seller1")

    def test_patch_block_public_user(self):
        self.client.force_authenticate(self.staff)
        r = self.client.patch(
            reverse("staff-user-detail", args=[self.public.id]),
            {"is_blocked": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.public.refresh_from_db()
        self.assertTrue(self.public.is_blocked)

    def test_cannot_block_self(self):
        self.client.force_authenticate(self.staff)
        r = self.client.patch(
            reverse("staff-user-detail", args=[self.staff.id]),
            {"is_blocked": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

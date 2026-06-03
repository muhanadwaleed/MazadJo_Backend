from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from cms.models import FAQ

User = get_user_model()


class CMSApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user", password="pass")
        FAQ.objects.create(
            question_en="Active?",
            question_ar="نشط؟",
            answer_en="Yes",
            answer_ar="نعم",
            is_active=True,
        )
        FAQ.objects.create(
            question_en="Hidden?",
            question_ar="مخفي؟",
            answer_en="No",
            answer_ar="لا",
            is_active=False,
        )

    def test_public_faq_lists_active_only(self):
        response = self.client.get("/api/v1/faqs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["question_en"], "Active?")

    def test_staff_can_create_faq(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/faqs/",
            {
                "question_en": "New?",
                "question_ar": "جديد؟",
                "answer_en": "Ok",
                "answer_ar": "حسنا",
                "sort_order": 1,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FAQ.objects.filter(question_en="New?").count(), 1)

    def test_non_staff_cannot_create_faq(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/faqs/",
            {
                "question_en": "Nope",
                "question_ar": "لا",
                "answer_en": "x",
                "answer_ar": "x",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

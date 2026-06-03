from rest_framework import serializers

from cms.models import ContactUs, FAQ, WhoUs, WhyUs


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = (
            "id",
            "question_ar",
            "question_en",
            "answer_ar",
            "answer_en",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class WhoUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhoUs
        fields = (
            "id",
            "title_ar",
            "title_en",
            "body_ar",
            "body_en",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class WhyUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhyUs
        fields = (
            "id",
            "title_ar",
            "title_en",
            "body_ar",
            "body_en",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = (
            "id",
            "phone",
            "email",
            "address_ar",
            "address_en",
            "social_links_json",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

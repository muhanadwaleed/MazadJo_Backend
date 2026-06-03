from django.db import models


class FAQ(models.Model):
    question_ar = models.CharField(max_length=512)
    question_en = models.CharField(max_length=512)
    answer_ar = models.TextField()
    answer_en = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cms_faqs"
        ordering = ["sort_order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self) -> str:
        return self.question_en


class WhoUs(models.Model):
    title_ar = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255)
    body_ar = models.TextField()
    body_en = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cms_who_us"
        ordering = ["sort_order", "id"]
        verbose_name = "Who us section"
        verbose_name_plural = "Who us sections"

    def __str__(self) -> str:
        return self.title_en


class WhyUs(models.Model):
    title_ar = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255)
    body_ar = models.TextField()
    body_en = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cms_why_us"
        ordering = ["sort_order", "id"]
        verbose_name = "Why us section"
        verbose_name_plural = "Why us sections"

    def __str__(self) -> str:
        return self.title_en


class ContactUs(models.Model):
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address_ar = models.TextField(blank=True)
    address_en = models.TextField(blank=True)
    social_links_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cms_contact_us"
        verbose_name = "Contact us"
        verbose_name_plural = "Contact us entries"

    def __str__(self) -> str:
        return self.email or self.phone or f"Contact #{self.pk}"

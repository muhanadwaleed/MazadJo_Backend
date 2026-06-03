from django.conf import settings
from django.db import models


class RatingIssueOption(models.Model):
    code = models.SlugField(max_length=64, unique=True)
    label_ar = models.CharField(max_length=255)
    label_en = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "rating_issue_options"

    def __str__(self) -> str:
        return self.code


class Rating(models.Model):
    class RoleContext(models.TextChoices):
        SELLER_RATES_WINNER = "seller_rates_winner", "Seller Rates Winner"
        WINNER_RATES_SELLER = "winner_rates_seller", "Winner Rates Seller"

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    rater_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings_given",
    )
    rated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings_received",
    )
    role_context = models.CharField(max_length=32, choices=RoleContext.choices)
    score = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ratings"
        indexes = [
            models.Index(fields=["auction", "rater_user"]),
        ]

    def __str__(self) -> str:
        return f"Rating {self.score} on {self.auction_id}"


class RatingIssueReport(models.Model):
    rating = models.ForeignKey(
        Rating,
        on_delete=models.CASCADE,
        related_name="issue_reports",
    )
    selected_issue_option = models.ForeignKey(
        RatingIssueOption,
        on_delete=models.PROTECT,
        related_name="reports",
    )
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rating_issue_reports"

    def __str__(self) -> str:
        return f"Issue on rating {self.rating_id}"


class UserAlert(models.Model):
    class AlertType(models.TextChoices):
        WARNING = "warning", "Warning"
        FREEZE = "freeze", "Freeze"
        BAN_REVIEW = "ban_review", "Ban Review"
        MANUAL_REVIEW = "manual_review", "Manual Review"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_alerts",
    )
    alert_type = models.CharField(max_length=32, choices=AlertType.choices)
    reason = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_alerts"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.alert_type} for user {self.user_id}"


class Dispute(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="disputes",
    )
    opened_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="disputes_opened",
    )
    against_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes_against",
    )
    dispute_type = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "disputes"

    def __str__(self) -> str:
        return f"Dispute {self.auction_id} {self.status}"

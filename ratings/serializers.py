from rest_framework import serializers

from ratings.models import Dispute, Rating, RatingIssueOption, RatingIssueReport


class RatingIssueOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingIssueOption
        fields = ("id", "code", "label_ar", "label_en", "is_active")


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = (
            "id",
            "auction",
            "rater_user",
            "rated_user",
            "role_context",
            "score",
            "comment",
            "created_at",
        )
        read_only_fields = ("id", "rater_user", "created_at")


class RatingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ("auction", "rated_user", "role_context", "score", "comment")

    def create(self, validated_data):
        validated_data["rater_user"] = self.context["request"].user
        return super().create(validated_data)


class RatingIssueReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingIssueReport
        fields = ("id", "rating", "selected_issue_option", "details", "created_at")
        read_only_fields = ("id", "created_at")


class DisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = (
            "id",
            "auction",
            "opened_by_user",
            "against_user",
            "dispute_type",
            "status",
            "description",
            "created_at",
            "resolved_at",
        )
        read_only_fields = (
            "id",
            "opened_by_user",
            "status",
            "created_at",
            "resolved_at",
        )


class DisputeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = ("auction", "against_user", "dispute_type", "description")

    def create(self, validated_data):
        validated_data["opened_by_user"] = self.context["request"].user
        return super().create(validated_data)

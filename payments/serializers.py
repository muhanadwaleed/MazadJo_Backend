from rest_framework import serializers

from payments.models import PaymentTransaction


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = (
            "id",
            "user",
            "related_entity_type",
            "related_entity_id",
            "transaction_type",
            "amount",
            "currency",
            "provider",
            "provider_reference",
            "method",
            "status",
            "initiated_at",
            "completed_at",
        )
        read_only_fields = fields


from rest_framework import serializers
from .models import Payment, Repayment


class CreatePaymentSerializer(serializers.Serializer):

    loan_id = serializers.IntegerField(min_value=1)

    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=0.01
    )

    provider = serializers.ChoiceField(
        choices=Payment.Provider.choices
    )

    phone_number = serializers.RegexField(
        regex=r"^\+?250[0-9]{9}$"
    )


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment

        fields = [
            "id",
            "loan",
            "provider",
            "amount",
            "currency",
            "phone_number",
            "status",
            "provider_reference",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class RepaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Repayment

        fields = [
            "id",
            "payment",
            "amount",
            "created_at",
        ]

        read_only_fields = fields

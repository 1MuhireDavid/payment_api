
from rest_framework import serializers
from .models import Loan


class LoanSerializer(serializers.ModelSerializer):

    class Meta:
        model = Loan
        fields = [
            "id",
            "principal_amount",
            "outstanding_balance",
            "currency",
            "status",
            "created_at",
        ]

        read_only_fields = fields

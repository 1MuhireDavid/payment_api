
import uuid

from django.db import models
from loans.models import Loan


class Payment(models.Model):

    class Provider(models.TextChoices):
        MTN = "MTN", "MTN Mobile Money"
        AIRTEL = "AIRTEL", "Airtel Money"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    provider = models.CharField(
        max_length=10,
        choices=Provider.choices
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=3,
        default="RWF"
    )

    phone_number = models.CharField(max_length=20)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    idempotency_key = models.UUIDField(
        unique=True
    )

    provider_reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    provider_transaction_id = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.status}"


class Repayment(models.Model):

    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="repayment"
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Repayment #{self.id}"


class ProviderEvent(models.Model):

    provider = models.CharField(max_length=10)

    event_id = models.CharField(max_length=150)

    payload = models.JSONField()

    processed = models.BooleanField(default=False)

    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"],
                name="unique_provider_event"
            )
        ]

    def __str__(self):
        return f"{self.provider} - {self.event_id}"

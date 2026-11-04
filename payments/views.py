
import uuid

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.generics import (
    RetrieveAPIView,
    ListAPIView
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import (
    ValidationError,
    NotFound
)

from loans.models import Loan

from .models import Payment, Repayment

from .serializers import (
    CreatePaymentSerializer,
    PaymentSerializer,
    RepaymentSerializer
)
from requests.exceptions import RequestException
from providers.services import get_payment_provider

class PaymentCreateView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = CreatePaymentSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        # Get idempotency key from request headers.
        raw_key = request.headers.get("Idempotency-Key")

        try:
            idempotency_key = uuid.UUID(raw_key or "")
        except (ValueError, TypeError):
            raise ValidationError({
                "Idempotency-Key": "A valid UUID is required."
            })

        data = serializer.validated_data

        # Check whether this request was already submitted.
        existing = Payment.objects.filter(
            idempotency_key=idempotency_key
        ).first()

        if existing:

            if (
                existing.loan.customer_id != request.user.id
                or existing.loan_id != data["loan_id"]
                or existing.amount != data["amount"]
                or existing.provider != data["provider"]
                or existing.phone_number != data["phone_number"]
            ):
                return Response(
                    {"error": "Idempotency key conflict."},
                    status=status.HTTP_409_CONFLICT
                )

            return Response(
                PaymentSerializer(existing).data,
                status=status.HTTP_200_OK
            )

        # Create payment while locking the loan row.
        try:
            with transaction.atomic():

                provider_service = get_payment_provider(payment.provider)
                provider_response = provider_service.initiate_payment(payment)

                loan = Loan.objects.select_for_update().get(
                    id=data["loan_id"],
                    customer=request.user,
                    status=Loan.Status.ACTIVE
                )

                # Calculate amounts already reserved by
                # other pending payment requests.
                pending_amount = (
                    Payment.objects.filter(
                        loan=loan,
                        status=Payment.Status.PENDING
                    ).aggregate(
                        total=Sum("amount")
                    )["total"] or Decimal("0.00")
                )

                available_balance = (
                    loan.outstanding_balance - pending_amount
                )

                if data["amount"] > available_balance:
                    raise ValidationError({
                        "amount": "Amount exceeds available loan balance."
                    })

                payment = Payment.objects.create(
                    loan=loan,
                    amount=data["amount"],
                    provider=data["provider"],
                    phone_number=data["phone_number"],
                    idempotency_key=idempotency_key,
                    currency=loan.currency,
                    status=Payment.Status.PENDING
                )

        except (RequestException, ValueError) as error:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])

            return Response(
                {
                    "message": "Unable to initiate payment.",
                    "payment_id": payment.id,
                    "detail": str(error),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Loan.DoesNotExist:
            raise NotFound(
                "Active loan not found for this customer."
            )

        # Payment is now recorded as pending.
        # Provider integration will be connected in the
        # next implementation phase.

        return Response(
            {
                "message": "Payment request submitted. Awaiting provider confirmation.",
                "payment": PaymentSerializer(payment).data,
                "provider_response": provider_response,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PaymentDetailView(RetrieveAPIView):

    serializer_class = PaymentSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Payment.objects.filter(
            loan__customer=self.request.user
        )


class PaymentListView(ListAPIView):

    serializer_class = PaymentSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Payment.objects.filter(
            loan__customer=self.request.user
        ).order_by("-created_at")


class RepaymentHistoryView(ListAPIView):

    serializer_class = RepaymentSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Repayment.objects.filter(
            payment__loan__customer=self.request.user
        ).order_by("-created_at")

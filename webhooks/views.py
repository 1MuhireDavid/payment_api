from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication

from payments.models import Payment, Repayment, ProviderEvent
from loans.models import Loan


class BasePaymentWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    provider_name = None

    def post(self, request):
        # IMPORTANT:
        # Verify the provider's callback authentication/signature here
        # before trusting or processing the payload.
        payload = request.data

        event_id = payload.get("event_id")
        reference = payload.get("reference")
        payment_status = payload.get("status")
        transaction_id = payload.get("transaction_id")

        if not all([event_id, reference, payment_status]):
            return Response(
                {"error": "Missing required callback fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment_status.upper() not in ["SUCCESS", "FAILED"]:
            return Response(
                {"message": "Callback received; no final status to process"},
                status=status.HTTP_200_OK,
            )

        try:
            with transaction.atomic():
                # Lock the loan first, then the payment.
                payment = get_object_or_404(
                    Payment.objects.select_related("loan"),
                    provider_reference=reference,
                    provider=self.provider_name,
                )

                loan = Loan.objects.select_for_update().get(
                    pk=payment.loan_id
                )

                payment = Payment.objects.select_for_update().get(
                    pk=payment.pk
                )

                ProviderEvent.objects.create(
                    provider=self.provider_name,
                    event_id=str(event_id),
                    payload=payload,
                    processed=False,
                )

                if payment.status in [
                    Payment.Status.SUCCESS,
                    Payment.Status.FAILED,
                ]:
                    return Response(
                        {"message": "Payment already finalized"},
                        status=status.HTTP_200_OK,
                    )

                if payment_status.upper() == "SUCCESS":
                    if payment.amount > loan.outstanding_balance:
                        return Response(
                            {"error": "Payment exceeds outstanding balance"},
                            status=status.HTTP_409_CONFLICT,
                        )

                    payment.status = Payment.Status.SUCCESS
                    payment.provider_transaction_id = transaction_id
                    payment.save()

                    Repayment.objects.create(
                        payment=payment,
                        amount=payment.amount,
                    )

                    loan.outstanding_balance -= payment.amount

                    if loan.outstanding_balance == 0:
                        loan.status = Loan.Status.PAID

                    loan.save(
                        update_fields=[
                            "outstanding_balance",
                            "status",
                            "updated_at",
                        ]
                    )

                else:
                    payment.status = Payment.Status.FAILED
                    payment.save(update_fields=["status", "updated_at"])

                ProviderEvent.objects.filter(
                    provider=self.provider_name,
                    event_id=str(event_id),
                ).update(processed=True)

        except IntegrityError:
            # A duplicate provider event has already been recorded.
            return Response(
                {"message": "Duplicate event received"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"message": "Webhook processed successfully"},
            status=status.HTTP_200_OK,
        )
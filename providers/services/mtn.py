import os
import uuid
import requests

from django.conf import settings
from .base import PaymentProvider


class MTNProvider(PaymentProvider):

    def get_access_token(self):
        url = f"{settings.MTN_BASE_URL}/collection/token/"

        response = requests.post(
            url,
            auth=(
                settings.MTN_SUBSCRIPTION_KEY,
                settings.MTN_API_USER
            ),
            headers={
                "Ocp-Apim-Subscription-Key":
                    settings.MTN_SUBSCRIPTION_KEY,
            },
            timeout=30,
        )

        response.raise_for_status()
        return response.json()["access_token"]

    def initiate_payment(self, payment):
        access_token = self.get_access_token()

        reference_id = str(payment.provider_reference)

        url = (
            f"{settings.MTN_BASE_URL}"
            "/collection/v1_0/requesttopay"
        )

        payload = {
            "amount": str(payment.amount),
            "currency": payment.currency,
            "externalId": str(payment.provider_reference),
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": payment.phone_number.replace("+", ""),
            },
            "payerMessage": "Loan repayment",
            "payeeNote": "Loan repayment",
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Reference-Id": reference_id,
            "X-Target-Environment": settings.MTN_TARGET_ENVIRONMENT,
            "Ocp-Apim-Subscription-Key": settings.MTN_SUBSCRIPTION_KEY,
            "Content-Type": "application/json",
            "X-Callback-Url": settings.MTN_CALLBACK_URL,
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        return {
            "provider_reference": reference_id,
            "status": "PENDING",
            "response": response.text,
        }
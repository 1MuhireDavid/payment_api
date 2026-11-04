import requests

from django.conf import settings
from .base import PaymentProvider


class AirtelProvider(PaymentProvider):

    def get_access_token(self):
        response = requests.post(
            settings.AIRTEL_AUTH_URL,
            json={
                "client_id": settings.AIRTEL_CLIENT_ID,
                "client_secret": settings.AIRTEL_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "*/*",
            },
            timeout=30,
        )

        response.raise_for_status()
        return response.json()["access_token"]

    def initiate_payment(self, payment):
        access_token = self.get_access_token()

        payload = {
            "reference": str(payment.provider_reference),
            "subscriber": {
                "country": settings.AIRTEL_COUNTRY,
                "currency": payment.currency,
                "msisdn": payment.phone_number.replace("+", ""),
            },
            "transaction": {
                "amount": str(payment.amount),
                "country": settings.AIRTEL_COUNTRY,
                "currency": payment.currency,
                "id": str(payment.provider_reference),
            },
        }

        response = requests.post(
            settings.AIRTEL_COLLECTION_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "*/*",
            },
            timeout=30,
        )

        response.raise_for_status()

        return {
            "status": "PENDING",
            "response": response.json(),
        }
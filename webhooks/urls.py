from django.urls import path
from .views import BasePaymentWebhookView


class MTNWebhookView(BasePaymentWebhookView):
    provider_name = "MTN"


class AirtelWebhookView(BasePaymentWebhookView):
    provider_name = "AIRTEL"


urlpatterns = [
    path("mtn/", MTNWebhookView.as_view(), name="mtn-webhook"),
    path("airtel/", AirtelWebhookView.as_view(), name="airtel-webhook"),
]
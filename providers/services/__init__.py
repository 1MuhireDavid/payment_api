from .mtn import MTNProvider
from .airtel import AirtelProvider


def get_payment_provider(provider_name):
    providers = {
        "MTN": MTNProvider,
        "AIRTEL": AirtelProvider,
    }

    provider_class = providers.get(provider_name)

    if not provider_class:
        raise ValueError("Unsupported payment provider")

    return provider_class()
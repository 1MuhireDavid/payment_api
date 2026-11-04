from abc import ABC, abstractmethod


class PaymentProvider(ABC):

    @abstractmethod
    def initiate_payment(self, payment):
        """
        Send a payment request to the mobile money provider.
        Must return the provider's response.
        """
        pass

from django.urls import path

from .views import (
    PaymentCreateView,
    PaymentDetailView,
    PaymentListView,
    RepaymentHistoryView
)

urlpatterns = [

    path(
        "",
        PaymentCreateView.as_view(),
        name="create-payment"
    ),

    path(
        "history/",
        PaymentListView.as_view(),
        name="payment-history"
    ),

    path(
        "repayments/",
        RepaymentHistoryView.as_view(),
        name="repayment-history"
    ),

    path(
        "<int:pk>/",
        PaymentDetailView.as_view(),
        name="payment-detail"
    ),
]

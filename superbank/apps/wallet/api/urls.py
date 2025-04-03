from django.urls import path

from .views import CreateTransactionView, GetWalletBalanceView

urlpatterns = [
    path("<str:wallet_uuid>/operation/", CreateTransactionView.as_view(), name="create-transaction"),
    path("<str:wallet_uuid>/", GetWalletBalanceView.as_view(), name="wallet-balance"),
]

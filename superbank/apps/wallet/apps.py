from django.apps import AppConfig
from django.urls import include, path


class WalletConfig(AppConfig):
    label = "wallet"
    name = "apps.wallet"
    verbose_name = "Кошелек"

    namespace = "wallet"

    def get_urls(self):
        return [
            path(
                "api/v1/wallets/", include("apps.wallet.api.urls"), name="wallet-api-v1"
            )
        ]

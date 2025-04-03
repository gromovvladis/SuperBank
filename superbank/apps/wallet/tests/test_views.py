import uuid
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.wallet.models import Wallet


class CreateTransactionViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.wallet = Wallet.objects.create(balance=Decimal("1000.00"))
        self.valid_deposit_payload = {"operation_type": "DEPOSIT", "amount": "500.00"}
        self.valid_withdraw_payload = {"operation_type": "WITHDRAW", "amount": "300.00"}
        self.url = reverse("create-transaction", args=[self.wallet.uuid])

    def test_transaction_with_non_existing_wallet(self):
        """Тест транзакции для несуществующего кошелька"""
        invalid_uuid = uuid.uuid4()
        url = reverse("create-transaction", args=[invalid_uuid])
        response = self.client.post(url, self.valid_deposit_payload)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_transaction_with_invalid_data(self):
        """Тест с некорректными данными"""
        invalid_payloads = [
            {"amount": "500.00"},  # Нет operation_type
            {"operation_type": "DEPOSIT"},  # Нет amount
            {"operation_type": "INVALID", "amount": "500.00"},  # Неверный тип
            {"operation_type": "DEPOSIT", "amount": "-100.00"},  # Отрицательная сумма
        ]

        for payload in invalid_payloads:
            response = self.client.post(self.url, payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_deposit_transaction(self):
        """Тест успешного пополнения"""
        response = self.client.post(self.url, self.valid_deposit_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.wallet.refresh_from_db()

        # Проверка баланса
        self.assertEqual(self.wallet.balance, Decimal("1500.00"))

        # Проверка структуры ответа
        response_data = response.data
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["transaction"]["type"], "deposit")
        self.assertEqual(response_data["transaction"]["amount"], "500.00")

    def test_successful_withdraw_transaction(self):
        """Тест успешного снятия средств"""
        response = self.client.post(self.url, self.valid_withdraw_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("700.00"))

    def test_withdraw_with_insufficient_funds(self):
        """Тест снятия при недостаточном балансе"""
        payload = {"operation_type": "WITHDRAW", "amount": "1500.00"}
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Недостаточно средств", response.data["error"])


class GetWalletBalanceViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.wallet = Wallet.objects.create(balance=Decimal("2000.00"))
        self.url = reverse("wallet-balance", args=[self.wallet.uuid])

    def test_get_non_existing_wallet(self):
        """Тест запроса несуществующего кошелька"""
        invalid_uuid = uuid.uuid4()
        url = reverse("wallet-balance", args=[invalid_uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_wallet_balance(self):
        """Тест получения баланса"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["wallet"]["balance"], "2000.00")
        self.assertEqual(response.data["wallet"]["uuid"], str(self.wallet.uuid))

    def test_balance_after_transactions(self):
        """Тест изменения баланса после операций"""
        # Создаем несколько транзакций
        self.wallet.deposit(Decimal("500.00"))
        self.wallet.withdraw(Decimal("300.00"))

        response = self.client.get(self.url)
        self.assertEqual(response.data["wallet"]["balance"], "2200.00")

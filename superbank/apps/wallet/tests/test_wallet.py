import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D

from django.test import TestCase, TransactionTestCase

from apps.wallet.api.exceptions import (InvalidAmountException,
                                        InvalidTypeException)
from apps.wallet.models import Transaction, Wallet


class WalletModelTest(TestCase):
    def setUp(self):
        self.wallet = Wallet.objects.create(balance=D("1000.00"))
        self.initial_balance = self.wallet.balance
        self.initial_updated = self.wallet.date_updated

    def test_wallet_creation(self):
        """Тест создания кошелька"""
        self.assertTrue(isinstance(self.wallet, Wallet))
        self.assertEqual(self.wallet.balance, D("1000.00"))
        self.assertIsNotNone(self.wallet.uuid)
        self.assertIsNotNone(self.wallet.date_created)

    def test_deposit_transaction(self):
        """Тест успешного пополнения"""
        amount = D("500.00")
        time.sleep(0.1)
        self.wallet.deposit(amount)

        self.assertEqual(self.wallet.balance, self.initial_balance + amount)
        self.assertGreater(self.wallet.date_updated, self.initial_updated)

        transaction = self.wallet.transactions.first()
        self.assertEqual(transaction.operation_type, Transaction.DEPOSIT)
        self.assertEqual(transaction.amount, amount)

    def test_withdraw_transaction(self):
        """Тест успешного снятия"""
        amount = D("300.00")
        time.sleep(0.1)
        self.wallet.withdraw(amount)

        self.assertEqual(self.wallet.balance, self.initial_balance - amount)
        self.assertGreater(self.wallet.date_updated, self.initial_updated)

        transaction = self.wallet.transactions.first()
        self.assertEqual(transaction.operation_type, Transaction.WITHDRAW)
        self.assertEqual(transaction.amount, amount)

    def test_insufficient_funds_withdraw(self):
        """Тест снятия при недостаточном балансе"""
        amount = self.wallet.balance + D("1.00")
        with self.assertRaises(InvalidAmountException) as context:
            self.wallet.withdraw(amount)

        self.assertIn("Недостаточно средств", str(context.exception))

    def test_negative_amount_deposit(self):
        """Тест пополнения отрицательной суммой"""
        with self.assertRaises(InvalidAmountException):
            self.wallet.deposit(D("-100.00"))

    def test_zero_amount_transaction(self):
        """Тест нулевой суммы транзакции"""
        with self.assertRaises(InvalidAmountException):
            self.wallet.deposit(D("0.00"))

    def test_invalid_transaction_type(self):
        """Тест невалидного типа транзакции"""
        with self.assertRaises(InvalidTypeException):
            self.wallet.transaction(D("100.00"), "invalid_type")


class WalletModelConcurrentTest(TransactionTestCase):

    def setUp(self):
        self.wallet = Wallet.objects.create(balance=D("1000.00"))
        self.initial_balance = self.wallet.balance

    def test_concurrent_updates(self):
        """Тест конкурентного обновления баланса"""
        initial_balance = self.wallet.balance

        num_threads = 10
        deposit_amount = 300

        def deposit_task(wallet_id):
            wallet = Wallet.objects.get(pk=wallet_id)
            wallet.deposit(deposit_amount)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(deposit_task, self.wallet.pk)
                for _ in range(num_threads)
            ]
            for future in futures:
                future.result()

        self.wallet.refresh_from_db()

        expected_balance = initial_balance + num_threads * deposit_amount

        self.assertEqual(
            self.wallet.balance,
            expected_balance,
            f"Баланс должен быть {expected_balance}, но получили {self.wallet.balance}",
        )


class WalletBalanceTest(TestCase):
    def test_balance_update_consistency(self):
        """Тест согласованности обновления баланса"""
        wallet = Wallet.objects.create(balance=D("1000.00"))

        # Серия операций
        operations = [
            ("deposit", D("200.00")),
            ("withdraw", D("300.00")),
            ("deposit", D("500.00")),
            ("withdraw", D("400.00")),
        ]

        for op_type, amount in operations:
            if op_type == "deposit":
                wallet.deposit(amount)
            else:
                wallet.withdraw(amount)

        self.assertEqual(wallet.balance, D("1000.00"))

    def test_precision_handling(self):
        """Тест обработки десятичных значений"""
        wallet = Wallet.objects.create(balance=D("0.00"))
        wallet.deposit(D("0.10"))
        wallet.deposit(D("0.20"))

        self.assertEqual(wallet.balance, D("0.30"))

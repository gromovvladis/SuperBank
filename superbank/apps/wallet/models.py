import logging
import random
import time
import uuid
from decimal import Decimal as D

from django.db import models, transaction
from django.db.models import F
from django.db.utils import DatabaseError, OperationalError
from django.utils import timezone

from apps.wallet.api.exceptions import InvalidAmountException, InvalidTypeException

logger = logging.getLogger("apps.wallet")


class Wallet(models.Model):
    """
    Объект кошелька.

    Содержит информацию о балансе и имеет уникальный идентификатор страндарта uuid.
    Хранит информацию о времи созданя и о времени изменения баланса.

    Функционал полей: owner, last_transaction_uuid не реализован, так как информация о пользователе и
    уникальный код транзакции не содержится в теле запроса, но хорошо было бы это реальзовать.

    """

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    balance = models.DecimalField(
        blank=False, default=0, max_digits=12, decimal_places=2
    )

    date_created = models.DateTimeField("Дата создания", auto_now_add=True)
    date_updated = models.DateTimeField("Дата изменения баланса", auto_now=True)

    # owner = models.ForeignKey(
    #     "auth.User",
    #     blank=True,
    #     related_name="wallets",
    #     on_delete=models.CASCADE,
    #     verbose_name="Владелец кошелька",
    # )
    # last_transaction_uuid = models.UUIDField("UUID последней транзакции", blank=True)
    # currency = models.CharField("Валюта", max_length=12, default=get_default_currency)

    class Meta:
        app_label = "wallet"
        verbose_name = "Кошелек"
        verbose_name_plural = "Кошельки"

    def __str__(self):
        return "Кошелек (uuid: {uuid}, Баланс {balance}".format(
            uuid=self.uuid, balance=self.balance
        )

    def transaction(self, amount, tnx_type):
        """Обработка транзакции с проверкой типа."""
        if tnx_type == Transaction.DEPOSIT:
            return self.deposit(amount)
        elif tnx_type == Transaction.WITHDRAW:
            return self.withdraw(amount)
        else:
            raise InvalidTypeException("Неверный тип транзакции")

    def deposit(self, amount):
        """
        Операция по внесению средст на данный кошелек.

        Получает сумму транзации в формате int, float
        создает транзацию и увеличивает баланс.

        """
        self._create_transaction(amount=amount, txn_type=Transaction.DEPOSIT)

    deposit.alters_data = True

    def withdraw(self, amount):
        """
        Операция по снятию средст с данного кошелека.

        Получает сумму транзации в формате int, float
        создает транзацию снятия наличных и уменьшает баланс.

        """
        self._create_transaction(amount=amount, txn_type=Transaction.WITHDRAW)

    withdraw.alters_data = True

    def _create_transaction(self, amount, txn_type, retries=10):
        """
        Создание записи о транзакции.

        Возможно будет более правильным создавать транзакцию при получении POST запроса из
        объекта транизации, а не из объекта кошелька,
        и уже при создании транзакции получать кошелек при помощи select_for_update и тем
        самым блокировать его для других транзакций.

        Но это уже зависит от контекста.

        1. Вализируем сумму транзакции.
        2. Блокируем данный кошелек для других транзакций.
        3. Создаем транзакцию.
        4. Изменяем баланс кошелька.
        5. Сохраняем изменения.
        6. В случае Race Condition выполняем попытки еще 10 раз с разным интервалом.
        7. Откатываем изменения в случае ошибки.
        8. Обновляем объект их базы данных для получения обновленных данных.

        """
        self._validate_amount(amount, txn_type)

        for attempt in range(retries):
            try:
                with transaction.atomic():
                    wallet = self.__class__.objects.select_for_update().get(pk=self.pk)
                    wallet.transactions.create(amount=amount, operation_type=txn_type)
                    wallet._change_balance(amount, txn_type)
                    break
            except (OperationalError, DatabaseError) as e:
                if attempt == retries - 1:
                    logger.error(
                        f"Ошибка при создании транзакции у кошелька {self.pk}. Превышено количество попыток. Ошибка: {e}."
                    )
                    raise OperationalError("Ошибка при создании транзакции")
                sleep_time = min(0.1 * (2**attempt) + random.uniform(0, 0.5), 2.0)
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(
                    f"Ошибка при создании транзакции у кошелька {self.pk}. Ошибка: {e}"
                )
                raise e

        self.refresh_from_db()

    def _change_balance(self, amount, txn_type):
        """Изменение баланса с сохранением."""
        amount_to_change = amount if txn_type == Transaction.DEPOSIT else -amount
        self.balance = F("balance") + D(amount_to_change)
        self.date_updated = timezone.now()
        self.save(update_fields=["balance", "date_updated"])

    def _validate_amount(self, amount, tnx_type):
        """Валидация суммы транзакции."""
        if D(amount) <= 0:
            raise InvalidAmountException(
                "Неверное значение суммы транзакции. Сумма транзакции отрицательная или равна 0"
            )

        if tnx_type == Transaction.WITHDRAW:
            self._validate_balance_for_withdraw(amount)

        return True

    def _validate_balance_for_withdraw(self, amount):
        """Проверка достаточности баланса для снятия."""
        if D(self.balance) < D(amount):
            raise InvalidAmountException(
                "Недостаточно средств для снятия. Сумма транзакции: {amount}. Баланс: {balance}".format(
                    amount=amount, balance=self.balance
                )
            )


class Transaction(models.Model):
    """
    Объект транзакции.

    Отображает информацию о проведенной транзакции:
        сумма транзации, кошелек, тип траезации, валюта транзации и дата создания.

    Поле status не реализовано, так как нет эндпоинтов для отмены транизакций. А значит все транзикции будут
    иметь статус "Успешно", так как создание транзакции происходит только при успешном завершении операции.
    Каждая транзакция также должна иметь уникальный идентификатор.

    """

    wallet = models.ForeignKey(
        "wallet.Wallet",
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Кошелек",
    )

    DEPOSIT, WITHDRAW = "deposit", "withdraw"
    TYPE_CHOICES = (
        (DEPOSIT, "Внесение средств"),
        (WITHDRAW, "Изъятие средств"),
    )

    operation_type = models.CharField(
        "Тип операции", choices=TYPE_CHOICES, max_length=255, blank=False, null=False
    )
    amount = models.DecimalField("Сумма транзакции", max_digits=12, decimal_places=2)

    date_created = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
    )

    # SUCCESS, ERROR, CANCEL = "success", "error", "cancel"
    # STATUS_CHOICES = (
    #     (SUCCESS, "Успешно"),
    #     (ERROR, "Успешно"),
    #     (CANCEL, "Отменена"),
    # )
    # status = models.CharField("Статус", max_length=12, choices=STATUS_CHOICES)
    # uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # currency = models.CharField("Валюта", max_length=12, default=get_default_currency)

    class Meta:
        app_label = "wallet"
        ordering = ["date_created", "wallet"]
        verbose_name = "Транзиция"
        verbose_name_plural = "Транзакции"

    def __str__(self):
        return (
            "Транзакция в кошелке: {uuid}, тип: {operation_type}, сумма: {amount}"
        ).format(
            uuid=self.wallet.uuid,
            operation_type=self.operation_type,
            amount=self.amount,
        )

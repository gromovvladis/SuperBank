import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallet.api.serializers import TransactionSerializer
from apps.wallet.models import Wallet

logger = logging.getLogger("apps.wallet")


class CreateTransactionView(APIView):
    """

    1. Для создания транзакции кошелек должен быть создан.
    Если кошелек не существует, то возвращается ошибка 404.
    Кошелек можно создать вручную через админку, либо реализовать эндпоинт
    для создание кошелька.
    2. Для создания транзакции необходимо передать в теле запроса:
        - operation_type: "DEPOSIT" или "WITHDRAW"
        - amount: сумма транзакции
    3. При успешном создании транзакции возвращается статус 201.
    4. При некорректном запросе возвращается ошибка 400.

    Использование сериализатора для валидации данных в данном примере излишне, но при большем количестве
    полей в запросе, а также при необходимости валидации данных, использование сериализатора является
    более предпочтительным.

    Запрос:
    POST api/v1/wallets/<WALLET_UUID>/operation
        {
            operation_type: “DEPOSIT” or “WITHDRAW”,
            amount: 1000
        }

    """

    permission_classes = [AllowAny]
    authentication_classes = [BasicAuthentication]
    serializer_class = TransactionSerializer
    http_method_names = ["post"]

    def post(self, request, wallet_uuid, *args, **kwargs):
        try:
            wallet = Wallet.objects.get(uuid=wallet_uuid)
        except Wallet.DoesNotExist:
            logger.warning(f"Кошелек не найден: {wallet_uuid}")
            return Response(
                {"error": "Кошелек не найден"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Некорректный запрос: {serializer.errors}")
            return Response(
                {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            return self._process_transaction(wallet, serializer.validated_data)
        except ValueError as e:
            logger.error(f"Ошибка при создании транзакции: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _process_transaction(self, wallet, validated_data):
        """Обработка успешной транзакции"""
        operation_type = validated_data["operation_type"]
        amount = validated_data["amount"]

        # Выполняем транзакцию
        wallet.transaction(amount=amount, tnx_type=operation_type)

        # Формируем ответ
        response_data = {
            "status": "success",
            "wallet": {
                "uuid": str(wallet.uuid),
                "balance": str(wallet.balance),
            },
            "transaction": {
                "amount": str(amount),
                "type": operation_type,
                "timestamp": timezone.now().isoformat(),
            },
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class GetWalletBalanceView(APIView):
    """

    Возвращает текущий баланс кошелька.
    Если кошелек не найден, возвращается ошибка 404.

    Запрос:
    GET api/v1/wallets/{WALLET_UUID}

    """

    permission_classes = [AllowAny]
    authentication_classes = [BasicAuthentication]
    serializer_class = TransactionSerializer
    http_method_names = ["get"]

    def get(self, request, wallet_uuid, *args, **kwargs):
        try:
            wallet = Wallet.objects.get(uuid=wallet_uuid)
        except Wallet.DoesNotExist:
            logger.warning(f"Кошелек не найден: {wallet_uuid}")
            return Response(
                {"error": "Кошелек не найден"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "status": "success",
                "wallet": {
                    "uuid": str(wallet.uuid),
                    "balance": str(wallet.balance),
                },
            }
        )

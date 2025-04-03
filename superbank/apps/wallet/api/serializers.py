from rest_framework import serializers

from apps.wallet.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """Сериализатор для транзакций."""

    operation_type = serializers.ChoiceField(
        choices=Transaction.TYPE_CHOICES,
        required=True,
        error_messages={
            "required": "Необходимо указать тип транзакции",
            "invalid_choice": "Некорректный тип транзакции",
        },
    )
    amount = serializers.DecimalField(
        required=True,
        max_digits=12,
        decimal_places=2,
        error_messages={
            "required": "Необходимо указать сумму транзакции",
            "invalid": "Некорректная сумма",
        },
    )

    def to_internal_value(self, data):
        data = dict(data.items())

        if "operation_type" in data:
            data["operation_type"] = data["operation_type"].lower()

        return super().to_internal_value(data)

    class Meta:
        model = Transaction
        fields = (
            "operation_type",
            "amount",
        )

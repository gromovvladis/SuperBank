from django.contrib import admin
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .models import Transaction, Wallet


def update_wallet_balance(wallet):
    """
    Обновляет баланс кошелька.
    """
    tnx_sum = wallet.transactions.aggregate(
        deposits=Sum("amount", filter=Q(operation_type=Transaction.DEPOSIT)),
        withdraws=Sum("amount", filter=Q(operation_type=Transaction.WITHDRAW)),
    )
    new_balance = (tnx_sum["deposits"] or 0) - (tnx_sum["withdraws"] or 0)
    wallet.balance = new_balance
    wallet.date_updated = timezone.now()
    wallet.save()


class TransactionInline(admin.TabularInline):
    model = Transaction
    readonly_fields = ("date_created",)

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "balance",
        "date_created",
        "date_updated",
    )
    readonly_fields = (
        "uuid",
        "balance",
        "date_created",
        "date_updated",
    )
    inlines = [TransactionInline]

    def save_formset(self, request, form, formset, change):
        """
        После сохранения транзакции пересчитываем баланс кошелька.
        Здесь валидация не выполняется.
        То есть, балан может быть отрицательным.
        """
        instances = formset.save(commit=False)
        deleted_instances = formset.deleted_objects

        with transaction.atomic():
            for obj in deleted_instances:
                obj.delete()

            for obj in instances:
                obj.save()

            wallet = form.instance
            update_wallet_balance(wallet)


class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "wallet",
        "operation_type",
        "amount",
        "date_created",
    )
    readonly_fields = ("id", "wallet", "date_created")

    def save_model(self, request, obj, form, change):
        """
        После сохранения транзакции пересчитываем баланс кошелька.
        """
        with transaction.atomic():
            obj.save()
            wallet = obj.wallet
            update_wallet_balance(wallet)


admin.site.register(Wallet, WalletAdmin)
admin.site.register(Transaction, TransactionAdmin)

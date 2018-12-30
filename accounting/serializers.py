from __future__ import annotations
from typing import TYPE_CHECKING
from rest_framework import serializers
from accounts.models import Account
from movements.serializers import TransactionSerializer
# !!!! TODO -> Bring MOneySerializer here
from movements.serializers import MoneySerializer

if TYPE_CHECKING:
    from accounting.balance import Balance


class BalanceSerializer(serializers.BaseSerializer):

    def to_representation(self, obj: Balance):
        moneys = obj.get_moneys()
        return MoneySerializer(many=True).to_representation(moneys)


class JournalSerializer(serializers.Serializer):
    account = serializers.PrimaryKeyRelatedField(read_only=True)
    initial_balance = BalanceSerializer()
    transactions = TransactionSerializer(many=True)
    balances = BalanceSerializer(many=True, source="get_balances")

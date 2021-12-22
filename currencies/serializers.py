from rest_framework import serializers as s

from common.models import N_DECIMAL_MAX_DIGITS, N_DECIMAL_PLACES

from .models import Currency
from .money import Balance, Money


class CurrencySerializer(s.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["pk", "name", "code", "imutable"]
        read_only_fields = ["pk", "imutable"]


class MoneySerializer(s.Serializer):
    quantity = s.DecimalField(N_DECIMAL_MAX_DIGITS, N_DECIMAL_PLACES)
    currency = s.PrimaryKeyRelatedField(queryset=Currency.objects.all())

    def create(self, validated_data):
        return Money(**validated_data)


class BalanceSerializer(s.BaseSerializer):
    def to_representation(self, obj: Balance):
        moneys = obj.get_moneys()
        return MoneySerializer(many=True).to_representation(moneys)

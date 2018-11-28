from rest_framework import serializers as s
from .models import Currency
from .money import Money
from common.models import N_DECIMAL_MAX_DIGITS, N_DECIMAL_PLACES


class MoneySerializer(s.Serializer):
    quantity = s.DecimalField(N_DECIMAL_MAX_DIGITS, N_DECIMAL_PLACES)
    currency = s.PrimaryKeyRelatedField(queryset=Currency.objects.all())

    def create(self, validated_data):
        return Money(**validated_data)


class CurrencySerializer(s.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['pk', 'name', 'imutable']
        read_only_fields = ['pk', 'imutable']

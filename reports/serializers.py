from rest_framework import serializers

from accounts.models import Account
from accounts.serializers import BalanceSerializer
from common.serializers import new_price_field
from currencies.currency_converter import (CurrencyPricePortifolio,
                                           DateAndPrice,)
from currencies.models import Currency
from currencies.serializers import MoneySerializer
from reports.reports import Period

from .view_models import FlowEvolutionInput, CurrencyOpts


def _new_account_field():
    return serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())


def _new_currency_field():
    return serializers.SlugRelatedField(
        queryset=Currency.objects.all(),
        slug_field='code',
    )


def _new_account_list_serializer():
    return serializers.ListSerializer(child=_new_account_field())


def _new_periods_serializer():

    def validator(x):
        if len(x) == 0:
            msg = 'At least one period must be passed'
            raise serializers.ValidationError(msg)

    return serializers.ListSerializer(child=PeriodField(), validators=[validator])


class PeriodField(serializers.Field):

    def to_internal_value(self, data):
        if not isinstance(data, list) or len(data) != 2:
            raise serializers.ValidationError(
                "Incorrect format: expectd a list of 2 dates."
            )
        return Period(
            serializers.DateField().to_internal_value(data[0]),
            serializers.DateField().to_internal_value(data[1])
        )

    def to_representation(self, period):
        return [
            serializers.DateField().to_representation(period.start),
            serializers.DateField().to_representation(period.end)
        ]


class BalanceEvolutionInputSerializer(serializers.Serializer):
    accounts = _new_account_list_serializer()
    periods = serializers.ListSerializer(child=PeriodField())

    def get_data(self):
        self.is_valid(True)
        return self.validated_data


class BalanceEvolutionDataSerializer(serializers.Serializer):
    account = _new_account_field()
    initial_balance = BalanceSerializer()
    balance_evolution = BalanceSerializer(many=True)


class BalanceEvolutionOutputSerializer(serializers.Serializer):
    periods = _new_periods_serializer()
    data = serializers.ListSerializer(child=BalanceEvolutionDataSerializer())


class DateAndPriceSerialzier(serializers.Serializer):
    date = serializers.DateField()
    price = new_price_field()

    def create(self, data):
        return DateAndPrice(**data)


class CurrencyPricePortifolioSerializer(serializers.Serializer):
    currency = _new_currency_field()
    prices = serializers.ListSerializer(child=DateAndPriceSerialzier())

    def create(self, data):
        prices_data = data['prices']
        prices = self._create_prices(prices_data)
        return CurrencyPricePortifolio(currency=data['currency'], prices=prices)

    def _create_prices(self, data):
        field = self.fields['prices']
        return field.create(data)


class CurrencyOptsSerializer(serializers.Serializer):
    price_portifolio = serializers.ListSerializer(
        child=CurrencyPricePortifolioSerializer()
    )
    convert_to = _new_currency_field()

    def create(self, data):
        price_portifolio_data = data['price_portifolio']
        price_portifolio = self._create_price_portfilio(price_portifolio_data)
        return CurrencyOpts(
            price_portifolio=price_portifolio,
            convert_to=data['convert_to'],
        )

    def _create_price_portfilio(self, data):
        field = self.fields['price_portifolio']
        return field.create(data)


class FlowEvolutionInputSerializer(serializers.Serializer):
    periods = _new_periods_serializer()
    accounts = _new_account_list_serializer()
    currency_opts = CurrencyOptsSerializer(default=None)

    def create(self, data):
        currency_opts_data = data.get('currency_opts')
        currency_opts = self._create_currency_opts(currency_opts_data)
        return FlowEvolutionInput(
            periods=data['periods'],
            accounts=data['accounts'],
            currency_opts=currency_opts,
        )

    def _create_currency_opts(self, data):
        if not data:
            return None
        return self.fields['currency_opts'].create(data)


class FlowSerializer(serializers.Serializer):
    period = PeriodField()
    moneys = serializers.ListSerializer(child=MoneySerializer())


class FlowEvolutionDataSerializer(serializers.Serializer):
    account = _new_account_field()
    flows = serializers.ListSerializer(child=FlowSerializer())


class FlowEvolutionOutputSerializer(serializers.Serializer):
    data = serializers.ListSerializer(
        child=FlowEvolutionDataSerializer(),
        source='*'
    )

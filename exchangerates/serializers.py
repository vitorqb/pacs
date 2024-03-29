from rest_framework import serializers

import common.models
import common.serializers

from .view_models import ExchangeRateDataInputs, PostExchangeRatesInputs


class ExchangeRateDataInputsSerializer(serializers.Serializer):
    start_at = serializers.DateField()
    end_at = serializers.DateField()
    currency_codes = common.serializers.CurrencyCodesField()

    def create(self, data):
        return ExchangeRateDataInputs(**data)


class PostExchangeRatesInputsSerializer(serializers.Serializer):
    skip_existing = serializers.BooleanField(default=False)

    def create(self, data):
        return PostExchangeRatesInputs(**data)

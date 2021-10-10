from rest_framework import serializers
from .view_models import ExchangeRateDataInputs
import common.models
import common.serializers


class ExchangeRateDataInputsSerializer(serializers.Serializer):
    start_at = serializers.DateField()
    end_at = serializers.DateField()
    currency_codes = common.serializers.CurrencyCodesField()

    def create(self, data):
        return ExchangeRateDataInputs(**data)

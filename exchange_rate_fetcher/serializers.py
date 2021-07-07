from rest_framework import serializers
from .view_models import ExchangeRateDataInputs
import common.models
import common.serializers


class ExchangeRateDataInputsSerializer(serializers.Serializer):
    start_at = common.models.new_string_date_field()
    end_at = common.models.new_string_date_field()
    currency_codes = common.serializers.CurrencyCodesField()
    token = serializers.CharField(required=False, allow_null=True)

    def create(self, data):
        return ExchangeRateDataInputs(**data)

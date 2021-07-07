from rest_framework import serializers
from .view_models import ExchangeRateDataInputs
import common.models


class CurrencyCodesField(serializers.Field):
    """ Converts a string with comas into a list. """

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("Should be a string!")
        return data.split(",")


class ExchangeRateDataInputsSerializer(serializers.Serializer):
    start_at = common.models.new_string_date_field()
    end_at = common.models.new_string_date_field()
    currency_codes = CurrencyCodesField()
    token = serializers.CharField(required=False, allow_null=True)

    def create(self, data):
        return ExchangeRateDataInputs(**data)

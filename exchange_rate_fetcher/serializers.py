from rest_framework import serializers
from django.core.validators import RegexValidator
from .view_models import ExchangeRateDataInputs


# Regexp used to validate dates
_date_regex = "[0-9]{4}-[0-1][0-9]-[0-3][0-9]"


def _new_string_date_field():
    """ Returns a field for a date-like string """
    validators_ = [RegexValidator(_date_regex)]
    return serializers.CharField(validators=validators_)


class CurrencyCodesField(serializers.Field):
    """ Converts a string with comas into a list. """

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("Should be a string!")
        return data.split(",")


class ExchangeRateDataInputsSerializer(serializers.Serializer):
    start_at = _new_string_date_field()
    end_at = _new_string_date_field()
    currency_codes = CurrencyCodesField()

    def create(self, data):
        return ExchangeRateDataInputs(**data)

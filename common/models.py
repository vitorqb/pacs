from decimal import Decimal
from typing import List

import django.db.models as m
from django.core.validators import MinValueValidator
from rest_framework import serializers
from django.core.validators import RegexValidator

# We store decimals with:
#   - up to 20 digits
#   - 5 decimal places
# We COMPARE decimals with:
#   - 2 decimal places
N_DECIMAL_PLACES: int = 5
N_DECIMAL_MAX_DIGITS: int = 20
DECIMAL_PLACES: Decimal = Decimal('10') ** -N_DECIMAL_PLACES
N_DECIMAL_COMPARISON: int = 2


def new_money_quantity_field():
    """ Returns a new field to be used to store currency quantities """
    return m.DecimalField(max_digits=20, decimal_places=N_DECIMAL_PLACES)


def new_price_field():
    """ Returns a Fied to be used as price """
    return m.DecimalField(
        validators=[MinValueValidator(0, "Prices must be positive")],
        max_digits=N_DECIMAL_MAX_DIGITS,
        decimal_places=N_DECIMAL_PLACES
    )


# Regexp used to validate dates
_date_regex = "[0-9]{4}-[0-1][0-9]-[0-3][0-9]"


def new_string_date_field():
    """ Returns a field for a date-like string """
    validators_ = [RegexValidator(_date_regex)]
    return serializers.CharField(validators=validators_)


class NameField(m.CharField):
    """ Fields for names """
    MAX_LENGTH = 150

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = self.MAX_LENGTH
        kwargs['unique'] = True
        super().__init__(*args, **kwargs)


def full_clean_and_save(x: m.Model) -> m.Model:
    x.full_clean()
    x.save()
    return x


def list_to_queryset(lst: List[m.Model]) -> m.QuerySet:
    """ Converts a list of objects into a queryset. """
    if len(lst) == 0:
        return m.QuerySet().none()
    return type(lst[0]).objects.filter(pk__in=[x.pk for x in lst])

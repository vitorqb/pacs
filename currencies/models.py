from __future__ import annotations

import re
from typing import Optional

import attr
import django.db.models as m
from rest_framework import serializers as s
from rest_framework.exceptions import APIException

from common.models import NameField, full_clean_and_save


# ------------------------------------------------------------------------------
# Exceptions
class CurrencyCodeValidationError(s.ValidationError):
    status_code = 400
    default_detail = "Invalid value for currency code (must have 3 uppercase chars)"
    default_code = "invalid"


class MissingCodeForCurrency(APIException):
    status_code = 500
    default_code = "missing_currency_code"
    default_detail = (
        "Some of the currencies on the server db does not"
        ' yet have the "code" value set. Please fill them'
    )


# ------------------------------------------------------------------------------
# Models
def validate_currency_code(x):
    regex = re.compile(r"[A-Z]{3}")
    regex_matches = regex.search(str(x))
    if not regex_matches:
        raise CurrencyCodeValidationError()


def new_currency_code_field():
    return m.CharField(
        blank=False,
        null=True,
        unique=True,
        db_index=True,
        max_length=3,
        validators=[validate_currency_code],
    )


@attr.s()
class CurrencyFactory:
    """Encapsulates creation of currencies"""

    def __call__(self, name: str, code: str) -> Currency:
        """Creates a currency using name"""
        return full_clean_and_save(Currency(name=name, code=code))


class Currency(m.Model):

    ERR_MSGS = {"IMUTABLE_CURRENCY": "Currency {} is imutable."}

    #
    # Fields
    #
    name = NameField()
    code = new_currency_code_field()
    imutable = m.BooleanField(default=False)

    #
    # Methods
    #
    def get_name(self) -> str:
        return self.name

    def get_code(self) -> str:
        if not self.code:
            raise MissingCodeForCurrency()
        return self.code


# ------------------------------------------------------------------------------
# Services
_cached_default_currency: Optional[Currency] = None


def get_default_currency() -> Currency:
    """Returns the default Currency. Cached for efficiency."""
    global _cached_default_currency
    if _cached_default_currency is None:
        _cached_default_currency = Currency.objects.get(name="Dollar")
    return _cached_default_currency

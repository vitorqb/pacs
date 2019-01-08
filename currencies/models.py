from __future__ import annotations

from typing import Optional

import attr
import django.db.models as m

from common.models import NameField, full_clean_and_save


# ------------------------------------------------------------------------------
# Models
@attr.s()
class CurrencyFactory():
    """ Encapsulates creation of currencies """

    def __call__(self, name: str) -> Currency:
        """ Creates a currency using name """
        return full_clean_and_save(Currency(name=name))


class Currency(m.Model):

    ERR_MSGS = {
        "IMUTABLE_CURRENCY": "Currency {} is imutable."
    }

    #
    # Fields
    #
    name = NameField()
    imutable = m.BooleanField(default=False)

    #
    # Methods
    #
    def get_name(self) -> str:
        return self.name


# ------------------------------------------------------------------------------
# Services
_cached_default_currency: Optional[Currency] = None


def get_default_currency() -> Currency:
    """ Returns the default Currency. Cached for efficiency. """
    global _cached_default_currency
    if _cached_default_currency is None:
        _cached_default_currency = Currency.objects.get(name="Dollar")
    return _cached_default_currency

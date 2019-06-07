from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Dict

import attr

from currencies.money import Money

if TYPE_CHECKING:
    from currencies.models import Currency


class UnkownCurrencyForConversion(Exception):
    pass


@attr.s()
class CurrencyConverter:
    """ A converter for money, from one currency to the other """

    # A dict mapping currency code -> value in dollars for 1 currency unit
    _currency_code_to_value_dct: Dict[str, Decimal] = attr.ib()

    def __attrs_post_init__(self):
        # We always consider dollar to have value 1, it is our base currency.
        USD_value = self._currency_code_to_value_dct.get('USD', Decimal(1))
        assert USD_value == Decimal(1)
        self._currency_code_to_value_dct['USD'] = Decimal(1)

    def convert(self, money: Money, currency: Currency) -> Money:
        """ Converts `money` to a `money` with `currency` """
        # Skip if same currency
        if money.currency == currency:
            return money
        self._assert_known_currency(currency)
        self._assert_known_currency(money.currency)
        dest_currency_code = currency.get_code()
        dest_currency_value = self._currency_code_to_value_dct[dest_currency_code]
        orig_currency_code = money.currency.get_code()
        orig_currency_value = self._currency_code_to_value_dct[orig_currency_code]
        quantity_in_dollars = money.quantity * orig_currency_value
        quantity_in_dest_currency = quantity_in_dollars / dest_currency_value
        return Money(currency=currency, quantity=quantity_in_dest_currency)

    def _assert_known_currency(self, currency: Currency) -> None:
        if currency.get_code() not in self._currency_code_to_value_dct.keys():
            raise UnkownCurrencyForConversion()

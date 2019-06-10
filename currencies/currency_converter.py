from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Set

import attr
from rest_framework.exceptions import APIException

from currencies.money import Money

if TYPE_CHECKING:
    from currencies.models import Currency
    from datetime import date as Date


class UnkownCurrencyForConversion(APIException):
    status_code = 400
    default_code = 'unkown_currency_for_conversion'


class UnkownDateForCurrencyConversion(APIException):
    status_code = 400
    default_code = 'unkown_date_for_currency_conversion'
    default_detail = (
        'An attempt was made to convert money between currencies for'
        ' a date where there was not enough information on the currency'
        ' prices to perform the conversion. This probably means you did'
        ' not sent enough currency information for the operation you attempted.'
        ' Please review the data sent and try again with complete data.'
    )


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
        self._assert_known_currencies(money.currency, currency)
        dest_currency_code = currency.get_code()
        dest_currency_value = self._currency_code_to_value_dct[dest_currency_code]
        orig_currency_code = money.currency.get_code()
        orig_currency_value = self._currency_code_to_value_dct[orig_currency_code]
        quantity_in_dollars = money.quantity * orig_currency_value
        quantity_in_dest_currency = quantity_in_dollars / dest_currency_value
        return Money(currency=currency, quantity=quantity_in_dest_currency)

    def _assert_known_currencies(self, *currencies):
        for c in currencies:
            self._assert_known_currency(c)

    def _assert_known_currency(self, currency: Currency) -> None:
        if currency.get_code() not in self._currency_code_to_value_dct.keys():
            msg = (
                f'Missing data for currency with code {currency.get_code()}.'
                f' This usually means that you tried to call an operation passing'
                f' currency conversion options that were insufficient for the'
                f' operation requested. Please review it and try again.'
            )
            raise UnkownCurrencyForConversion(msg)


@attr.s(frozen=True)
class DateAndPrice:
    date: Date = attr.ib()
    price: Decimal = attr.ib()


@attr.s(frozen=True)
class CurrencyPricePortifolio:
    currency: Currency = attr.ib()
    prices: List[DateAndPrice] = attr.ib()

    def get_dates(self) -> Set[Date]:
        return set(x.date for x in self.prices)


class CurrencyPricePortifolioConverter:
    """
    A converted based on a currency price portifolio, which is a mapping of
    (currency, date) -> currency_price (in dollars).
    """
    _date_to_currency_prices: Dict[Date, Dict[str, Decimal]]
    _dates: Set[Date]

    def __init__(self, price_portifolio_list: List[CurrencyPricePortifolio]):
        self._dates = set()
        self._date_to_currency_prices = defaultdict(lambda: {})
        for price_portifolio in price_portifolio_list:
            currency = price_portifolio.currency
            for date_and_price in price_portifolio.prices:
                date = date_and_price.date
                price = date_and_price.price
                self._dates.add(date)
                self._date_to_currency_prices[date][currency.get_code()] = price

    def convert(self, money: Money, currency: Currency, date: Date) -> Money:
        if money.currency == currency:
            return money
        if date not in self._dates:
            raise UnkownDateForCurrencyConversion()
        currency_code_to_value = self._date_to_currency_prices[date]
        return CurrencyConverter(currency_code_to_value).convert(money, currency)

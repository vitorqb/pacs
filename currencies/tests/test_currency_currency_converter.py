from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from common.test import PacsTestCase
from currencies.currency_converter import (CurrencyConverter,
                                           CurrencyPricePortifolio,
                                           CurrencyPricePortifolioConverter,
                                           DateAndPrice,
                                           UnkownCurrencyForConversion,
                                           UnkownDateForCurrencyConversion)
from currencies.money import Money


class CurrencyConverterTestCase(PacsTestCase):
    pass


class TestCurrencyConverter(CurrencyConverterTestCase):

    @staticmethod
    def get_currency_value_dct():
        return {
            'EUR': Decimal('1.1'),
            'BRL': Decimal('0.25'),
            'JPY': Decimal('0.0025'),
        }

    def test_convert_same_currency(self):
        converter = CurrencyConverter(self.get_currency_value_dct())
        currency = Mock(code='BRL')
        quantity = 25
        money = Money(quantity=quantity, currency=currency)
        assert converter.convert(money, currency) == money

    def test_convert_to_dollar(self):
        currency_value_dct = self.get_currency_value_dct()
        converter = CurrencyConverter(currency_value_dct)

        real = Mock(get_code=lambda: 'BRL')
        dollar = Mock(get_code=lambda: 'USD')
        quantity = Decimal('10.25')
        money = Money(quantity=quantity, currency=real)

        exp_quantity = quantity * currency_value_dct['BRL']
        exp_money = Money(quantity=exp_quantity, currency=dollar)
        assert converter.convert(money, dollar) == exp_money

    def test_convert_from_dollar(self):
        currency_value_dct = self.get_currency_value_dct()
        converter = CurrencyConverter(currency_value_dct)

        real = Mock(get_code=lambda: 'BRL')
        dollar = Mock(get_code=lambda: 'USD')
        quantity = Decimal('111.1')
        money = Money(quantity=quantity, currency=dollar)

        exp_quantity = quantity / currency_value_dct['BRL']
        exp_money = Money(quantity=exp_quantity, currency=real)
        assert converter.convert(money, real) == exp_money

    def test_convert_no_dollar(self):
        currency_value_dct = self.get_currency_value_dct()
        converter = CurrencyConverter(currency_value_dct)

        real = Mock(get_code=lambda: 'BRL')
        euro = Mock(get_code=lambda: 'EUR')
        quantity = Decimal('100')
        money = Money(quantity=quantity, currency=real)

        exp_quantity_dollars = quantity * currency_value_dct['BRL']
        exp_quantity = exp_quantity_dollars / currency_value_dct['EUR']
        exp_money = Money(quantity=exp_quantity, currency=euro)
        assert converter.convert(money, euro) == exp_money

    def test_unkown_currency(self):
        currency_value_dct = self.get_currency_value_dct()
        converter = CurrencyConverter(currency_value_dct)
        unkown_currency = Mock(code='UNK')
        money_with_unkown_currency = Money(currency=unkown_currency, quantity=1)
        with self.assertRaises(UnkownCurrencyForConversion):
            converter.convert(money_with_unkown_currency, Mock())


class TestCurrencyPricePortifolio:

    def test_get_dates(self):
        currency = Mock()
        prices = [Mock(date=1), Mock(date=2)]
        currency_price_portifolio = CurrencyPricePortifolio(currency, prices)
        assert currency_price_portifolio.get_dates() == {1, 2}


class TestCurrencyPricePortifolioConverter(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.real = Mock(get_code=lambda: 'BRL')
        self.euro = Mock(get_code=lambda: 'EUR')

    def get_data(self):
        return [
            CurrencyPricePortifolio(
                currency=self.euro,
                prices=[
                    DateAndPrice(date=date(2019, 1, 1), price=Decimal(2)),
                    DateAndPrice(date=date(2019, 2, 1), price=Decimal(4)),
                ]
            ),
            CurrencyPricePortifolio(
                currency=self.real,
                prices=[
                    DateAndPrice(date=date(2019, 1, 1), price=Decimal('0.5')),
                    DateAndPrice(date=date(2019, 2, 1), price=Decimal('0.5')),
                    DateAndPrice(date=date(2019, 3, 1), price=Decimal('0.25')),
                ]
            )
        ]

    def get_converter(self, **kwargs):
        data = self.get_data(**kwargs)
        return CurrencyPricePortifolioConverter(data)

    def test_conversion_to_final_currency_always_works(self):
        # Convertion BRL -> BRL always works.
        converter = self.get_converter()
        five_reais = Money(quantity=5, currency=self.real)
        assert converter.convert(five_reais, self.real, date(2019, 1, 1)) == (
            five_reais
        )
        assert converter.convert(five_reais, self.real, date(1993, 11, 23)) == (
            five_reais
        )

    def test_conversion_between_currencies(self):
        # Convertion EUR -> BRL Only works for dates
        five_euros = Money(quantity=5, currency=self.euro)
        converter = self.get_converter()
        assert converter.convert(five_euros, self.real, date(2019, 1, 1)) == (
            Money(20, self.real)
        )
        assert converter.convert(five_euros, self.real, date(2019, 2, 1)) == (
            Money(40, self.real)
        )

    def test_conversion_fails_if_unkown_date(self):
        five_euros = Money(quantity=5, currency=self.euro)
        converter = self.get_converter()
        with self.assertRaises(UnkownDateForCurrencyConversion):
            converter.convert(five_euros, date(1993, 11, 23), self.real)

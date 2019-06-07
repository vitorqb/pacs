from decimal import Decimal
from unittest.mock import Mock
from common.test import PacsTestCase

from currencies.currency_converter import CurrencyConverter, UnkownCurrencyForConversion
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

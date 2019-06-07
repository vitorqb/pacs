from unittest.mock import Mock

from django.core.exceptions import ValidationError

from common.test import PacsTestCase
from currencies import models as currency_models
from currencies.management.commands.populate_currencies import \
    currency_populator
from currencies.models import (Currency, CurrencyCodeValidationError,
                               CurrencyFactory, get_default_currency,
                               new_currency_code_field, MissingCodeForCurrency)

from .factories import CurrencyTestFactory


class CurrencyModelTestCase(PacsTestCase):

    def setUp(self):
        super().setUp()


class TestNewCurrencyCodeField(CurrencyModelTestCase):

    def test_blank_invalid(self):
        field = new_currency_code_field()
        with self.assertRaises(ValidationError):
            field.clean("", Mock())

    def test_invalid(self):
        field = new_currency_code_field()
        for x in ["S", "AbC"]:
            with self.assertRaises(CurrencyCodeValidationError):
                field.clean(x, Mock())

    def test_valid(self):
        field = new_currency_code_field()
        for x in ["AAA", "EUR", "DOL"]:
            with self.subTest(x=x):
                assert field.run_validators(x) is None


class TestCurrencyFactory(CurrencyModelTestCase):

    @staticmethod
    def get_data(**kwargs):
        out = dict(kwargs).copy()
        if 'name' not in out:
            out['name'] = 'foo'
        if 'code' not in out:
            out['code'] = 'BAR'
        return out

    def test_base(self):
        data = self.get_data()
        cur = CurrencyFactory()(**data)
        assert cur in Currency.objects.all()
        assert cur.name == data['name']
        assert cur.code == data['code']

    def test_invalid_code(self):
        code = 'I'
        data = self.get_data(code=code)
        with self.assertRaises(CurrencyCodeValidationError):
            CurrencyFactory()(**data)


class TestCurrency(CurrencyModelTestCase):

    def test_get_name(self):
        assert CurrencyTestFactory(name="hola").get_name() == "hola"

    def test_get_code(self):
        assert CurrencyTestFactory(code="ABC").get_code() == "ABC"

    def test_get_code_for_none(self):
        for code in ("", None):
            currency = Mock(code=code)
            with self.assertRaises(MissingCodeForCurrency):
                Currency.get_code(currency)

    def test_currency_base(self):
        name = "a"
        code = "AAA"
        cur = CurrencyFactory()(name=name, code=code)
        assert cur.name == name
        assert cur.code == code


class TestFun_get_default_currency(CurrencyModelTestCase):

    def test_base(self):
        currency_populator()
        # Forcely removes cache
        currency_models._cached_default_currency = None
        dollar = Currency.objects.get(name="Dollar")
        with self.assertNumQueries(1):
            assert get_default_currency() == dollar
            # Repeats to test cache
            assert get_default_currency() == dollar

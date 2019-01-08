from common.test import PacsTestCase
from currencies import models as currency_models
from currencies.management.commands.populate_currencies import \
    currency_populator
from currencies.models import Currency, CurrencyFactory, get_default_currency


class CurrencyModelTestCase(PacsTestCase):

    def setUp(self):
        super().setUp()


class TestCurrencyFactory(CurrencyModelTestCase):

    def test_base(self):
        nm = "aloha"
        cur = CurrencyFactory()(nm)
        assert cur in Currency.objects.all()
        assert cur.name == nm


class TestCurrency(CurrencyModelTestCase):

    def test_get_name(self):
        assert CurrencyFactory()(name="hola").get_name() == "hola"

    def test_currency_base(self):
        name = "a"
        cur = CurrencyFactory()(name=name)
        assert cur.name == name


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

from pyrsistent import pvector
from common.test import PacsTestCase
from currencies.models import CurrencyFactory, Currency, get_default_currency
from currencies.management.commands.populate_currencies import currency_populator
from accounts.models import AccountFactory, AccTypeEnum, get_root_acc
from accounts.management.commands.populate_accounts import (
    account_type_populator,
    account_populator
)


class CurrencyModelTestCase(PacsTestCase):

    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()
        currency_populator()
        self.currency = CurrencyFactory()(name="Yen")
        self.accs = pvector(
            AccountFactory()(x, AccTypeEnum.LEAF, get_root_acc())
            for x in ("A", "B")
        )


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
        dollar = Currency.objects.get(name="Dollar")
        with self.assertNumQueries(1):
            assert get_default_currency() == dollar
            # Repeats to test cache
            assert get_default_currency() == dollar

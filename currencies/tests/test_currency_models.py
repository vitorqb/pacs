from pyrsistent import pvector
from common.test import TestCase
from currencies.models import CurrencyFactory
from currencies.management.commands.populate_currencies import currency_populator
from accounts.models import AccountFactory, AccTypeEnum, get_root_acc
from accounts.management.commands.populate_accounts import (
    account_type_populator,
    account_populator
)


class CurrencyModelTestCase(TestCase):

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


class CurrencyTestCase(CurrencyModelTestCase):

    def test_currency_base(self):
        name = "a"
        cur = CurrencyFactory()(name=name)
        assert cur.name == name

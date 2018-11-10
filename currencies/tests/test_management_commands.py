from common.test import TestCase
from common.models import full_clean_and_save
from currencies.models import Currency
from currencies.management.commands.populate_currencies import CurrencyPopulator
from pyrsistent import m, v


class ManagementCommandTestCase(TestCase):
    pass


class TestPopulateCurrencies(ManagementCommandTestCase):

    def setUp(self):
        super().setUp()
        self.name = "Yen"
        self.price = 210
        self.populator = CurrencyPopulator(
            currencies_data=v(m(name=self.name, base_price=self.price))
        )

    def test_base(self):
        assert not Currency.objects.filter(name=self.name).exists()
        self.populator()
        yen = Currency.objects.filter(name=self.name).get()
        assert yen.name == self.name
        assert yen.base_price == self.price

    def test_skip(self):
        yen = full_clean_and_save(Currency(name=self.name, base_price=self.price))
        self.populator()
        assert Currency.objects.get(name=self.name) == yen

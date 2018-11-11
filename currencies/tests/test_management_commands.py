import attr
from common.test import TestCase
from currencies.models import Currency, CurrencyFactory
from currencies.management.commands.populate_currencies import currency_populator
from pyrsistent import m, v


class ManagementCommandTestCase(TestCase):
    pass


class TestPopulateCurrencies(ManagementCommandTestCase):

    def setUp(self):
        super().setUp()
        self.name = "Yen"
        self.price = 210
        self.populator = attr.evolve(
            currency_populator,
            model_data=v(m(name=self.name, base_price=self.price))
        )

    def test_base(self):
        assert not Currency.objects.filter(name=self.name).exists()
        self.populator()
        yen = Currency.objects.get(name=self.name)
        assert yen.name == self.name
        assert yen.base_price == self.price

    def test_skip(self):
        yen = CurrencyFactory()(name=self.name, base_price=self.price)
        self.populator()
        assert Currency.objects.get(name=self.name) == yen

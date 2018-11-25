import attr
from common.test import PacsTestCase
from currencies.models import Currency, CurrencyFactory
from currencies.management.commands.populate_currencies import currency_populator
from pyrsistent import m, v


class ManagementCommandTestCase(PacsTestCase):
    pass


class TestPopulateCurrencies(ManagementCommandTestCase):

    def setUp(self):
        super().setUp()
        self.name = "Yen"
        self.populator = attr.evolve(
            currency_populator,
            model_data=v(m(name=self.name))
        )

    def test_base(self):
        assert not Currency.objects.filter(name=self.name).exists()
        self.populator()
        yen = Currency.objects.get(name=self.name)
        assert yen.name == self.name

    def test_skip(self):
        yen = CurrencyFactory()(name=self.name)
        self.populator()
        assert Currency.objects.get(name=self.name) == yen

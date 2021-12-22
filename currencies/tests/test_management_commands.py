import attr

from common.testutils import PacsTestCase
from currencies.management.commands.populate_currencies import currency_populator
from currencies.models import Currency, CurrencyFactory


class ManagementCommandTestCase(PacsTestCase):
    pass


class TestPopulateCurrencies(ManagementCommandTestCase):
    def setUp(self):
        super().setUp()
        self.name = "Yen"
        self.code = "JPY"
        self.populator = attr.evolve(
            currency_populator, model_data=[{"name": self.name, "code": self.code}]
        )

    def test_base(self):
        assert not Currency.objects.filter(name=self.name).exists()
        self.populator()
        assert Currency.objects.get(name=self.name, code=self.code) is not None

    def test_skip(self):
        yen = CurrencyFactory()(name=self.name, code=self.code)
        self.populator()
        assert Currency.objects.get(name=self.name, code=self.code) == yen

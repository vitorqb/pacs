from currencies.models import Currency, get_default_currency
from currencies.money import Money
from currencies.management.commands.populate_currencies import CurrencyPopulator
from common.test import TestCase
from common.utils import utcdatetime


class MoneyTestCase(TestCase):
    def setUp(self):
        super().setUp()
        CurrencyPopulator()()
        self.dollar = get_default_currency()
        self.euro = Currency.objects.get(name="Euro")
        self.money = Money(250, self.euro)
        self.dt = utcdatetime(2017, 1, 1)


class TestMoney(MoneyTestCase):

    def test_get_value_base(self):
        assert self.euro.get_price(self.dt) == 1.13
        assert self.money.get_value(self.dt) == int(round(250 * 1.13))

    def test_convert_base(self):
        assert self.money.convert(self.dollar, self.dt) == \
            Money(int(250 * 1.13), self.dollar)

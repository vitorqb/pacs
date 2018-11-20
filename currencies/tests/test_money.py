from decimal import Decimal
from currencies.models import Currency, get_default_currency
from currencies.money import Money
from currencies.management.commands.populate_currencies import currency_populator
from common.test import TestCase
from common.utils import utcdatetime


class MoneyTestCase(TestCase):
    def setUp(self):
        super().setUp()
        currency_populator()
        self.dollar = get_default_currency()
        self.euro = Currency.objects.get(name="Euro")
        self.money = Money(250, self.euro)
        self.dt = utcdatetime(2017, 1, 1)


class TestMoney(MoneyTestCase):

    def test_base(self):
        money = Money('10.24', self.euro)
        assert money.quantity == Decimal('10.24')
        assert money.currency == self.euro

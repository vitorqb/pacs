from unittest.mock import Mock
from currencies.money import Money
from common.test import TestCase


class MoneyTestCase(TestCase):
    pass


class TestMoney(MoneyTestCase):

    def test_change_currency(self):
        original, new, quantity = Mock(), Mock(), 10
        Money(quantity, original).change_currency(new) == Money(quantity, new)

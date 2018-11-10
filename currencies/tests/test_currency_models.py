from common.test import TestCase
from currencies.models import Currency


class CurrencyModelTestCase(TestCase):
    pass


class CurrencyTestCase(CurrencyModelTestCase):

    def test_currency_base(self):
        name, base_price = "a", 1
        cur = Currency.objects.create(name=name, base_price=base_price)
        assert cur.name == name
        assert cur.base_price == base_price

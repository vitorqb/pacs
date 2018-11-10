from django.core.exceptions import ValidationError
from common.test import TestCase
from common.models import full_clean_and_save
from currencies.models import Currency
from datetime import date, timedelta


class CurrencyModelTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.currency = Currency.objects.create(name="Real", base_price=200)


class CurrencyTestCase(CurrencyModelTestCase):

    def test_currency_base(self):
        name, base_price = "a", 1
        cur = Currency.objects.create(name=name, base_price=base_price)
        assert cur.name == name
        assert cur.base_price == base_price


class CurrencyTestCase_new_price_change(CurrencyModelTestCase):

    def setUp(self):
        super().setUp()
        self.dt = date(2018, 1, 1)
        self.new_price = 250

    def call(self):
        return self.currency.new_price_change(self.dt, self.new_price)

    def test_base(self):
        assert self.currency.currencypricechange_set.count() == 0
        price_change = self.call()
        assert self.currency.currencypricechange_set.count() == 1
        assert price_change.date == self.dt
        assert price_change.new_price == self.new_price

    def test_repeated_value_raises_validation_err(self):
        self.call()
        self.assertRaisesRegex(ValidationError, 'Date.+exists', self.call)

    def test_zero_value_raises_err(self):
        self.new_price = 0
        self.assertRaisesRegex(ValidationError, 'new_price.+positive', self.call)


class CurrencyTestCase_price_changes_iter(CurrencyModelTestCase):

    def test_empty(self):
        assert list(self.currency.price_changes_iter()) == []

    def test_one_long(self):
        dt, new_price = date(2018, 12, 1), 250
        price_change = self.currency.new_price_change(dt, new_price)
        assert list(self.currency.price_changes_iter()) == [price_change]


class CurrencyTestCase_price_changes_iter_until(CurrencyModelTestCase):

    def setUp(self):
        super().setUp()
        self.price_changes = [
            self.currency.new_price_change(d, p)
            for d, p in ((date(2016, 1, 1), 180),
                         (date(2016, 2, 2), 200),
                         (date(2017, 1, 13), 120))
        ]

    def test_none(self):
        dt = self.price_changes[0].date - timedelta(days=1)
        assert list(self.currency.price_changes_iter_until(dt)) == []

    def test_one(self):
        dt = self.price_changes[0].date
        assert list(self.currency.price_changes_iter_until(dt)) == \
            self.price_changes[:1]

    def test_all(self):
        dt = self.price_changes[2].date
        assert list(self.currency.price_changes_iter_until(dt)) == \
            self.price_changes

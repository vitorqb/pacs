from datetime import date, timedelta
from pyrsistent import v, pvector
from django.core.exceptions import ValidationError
from common.test import TestCase
from currencies.money import Money
from currencies.models import CurrencyFactory
from movements.models import TransactionFactory, MovementSpec
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
        self.currency = CurrencyFactory()(name="Yen", base_price=2)

    def set_up_price_changes(self):
        self.price_changes = [
            self.currency.new_price_change(d, p)
            for d, p in ((date(2016, 1, 1), 1.8),
                         (date(2016, 2, 2), 2),
                         (date(2017, 1, 13), 1.2))
        ]


class CurrencyTestCase(CurrencyModelTestCase):

    def test_currency_base(self):
        name, base_price = "a", 1
        cur = CurrencyFactory()(name=name, base_price=base_price)
        assert cur.name == name
        assert cur.base_price == base_price

    def test_currency_cant_have_negative_price(self):
        name, base_price = "a", -1
        with self.assertRaises(ValidationError):
            CurrencyFactory()(name=name, base_price=base_price)

    def test_cant_set_price_if_imutable(self):
        cur = CurrencyFactory()(name="hola", base_price=True)
        cur.imutable = True
        exp_err_msg = cur.ERR_MSGS['IMUTABLE_CURRENCY'].format(cur.name)
        with self.assertRaisesRegex(ValidationError, exp_err_msg):
            cur.new_price_change(date(2017, 1, 1), 20)


class CurrencyTestCase_new_price_change(CurrencyModelTestCase):

    def setUp(self):
        super().setUp()
        self.dt = date(2018, 1, 1)
        self.new_price = 2.50
        self.accs = pvector(
            AccountFactory()(x, AccTypeEnum.LEAF, get_root_acc())
            for x in ("A", "B")
        )

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
        self.new_price = -0.01
        self.assertRaisesRegex(ValidationError, 'new_price.+positive', self.call)

    def test_get_transactions(self):
        moneys = v(Money(100, self.currency), Money(-100, self.currency))
        movs_specs = pvector(MovementSpec(a, m) for a, m in zip(self.accs, moneys))
        dates = v(self.dt - timedelta(days=1), self.dt)

        trans = pvector(TransactionFactory()("_", d, movs_specs) for d in dates)
        assert pvector(self.currency.get_transactions(dates[0])) == trans
        assert pvector(self.currency.get_transactions(dates[1])) == trans[1:]
        assert pvector(self.currency.get_transactions(dates[1] + timedelta(days=1))) ==\
            pvector()

    def test_get_transactions_leave_out_if_not_same_cur(self):
        other_cur = CurrencyFactory()("A", 1)
        trans = TransactionFactory()(
            "_",
            self.dt,
            v(
                MovementSpec(self.accs[0], Money(100, other_cur)),
                MovementSpec(self.accs[1], Money(-100, other_cur))
            )
        )
        assert pvector(other_cur.get_transactions(self.dt)) == v(trans)
        assert pvector(self.currency.get_transactions(self.dt)) == pvector()


class CurrencyTestCase_price_changes_iter(CurrencyModelTestCase):

    def test_empty(self):
        assert list(self.currency.price_changes_iter()) == []

    def test_one_long(self):
        dt, new_price = date(2018, 12, 1), 2.5
        price_change = self.currency.new_price_change(dt, new_price)
        assert list(self.currency.price_changes_iter()) == [price_change]


class CurrencyTestCase_price_changes_iter_until(CurrencyModelTestCase):

    def setUp(self):
        super().setUp()
        self.set_up_price_changes()

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


class CurrencyTestCase_get_price(CurrencyModelTestCase):

    def setUp(self):
        super().setUp()
        self.set_up_price_changes()

    def call(self):
        return self.currency.get_price(self.dt)

    def test_base_price(self):
        self.dt = self.price_changes[0].date - timedelta(days=1)
        assert self.call() == self.currency.base_price

    def test_middle(self):
        self.dt = date(2017, 1, 4)
        assert self.dt < self.price_changes[-1].date and\
            self.dt > self.price_changes[-2].date
        assert self.call() == self.price_changes[-2].new_price

    def test_last(self):
        self.dt = self.price_changes[-1].date
        assert self.call() == self.price_changes[-1].new_price

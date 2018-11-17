from datetime import date, timedelta
from pyrsistent import v, pvector
from django.core.exceptions import ValidationError
from common.test import TestCase
from common.test_utils import TransactionBuilder, CurrencyBuilder
from currencies.money import Money
from currencies.models import CurrencyFactory
from currencies.management.commands.populate_currencies import currency_populator
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
        currency_populator()
        self.currency = CurrencyFactory()(name="Yen", base_price=2)
        self.accs = pvector(
            AccountFactory()(x, AccTypeEnum.LEAF, get_root_acc())
            for x in ("A", "B")
        )

    def set_up_price_changes(self):
        self.price_changes = pvector([
            self.currency.new_price_change(d, p)
            for d, p in ((date(2016, 1, 1), 1.8),
                         (date(2016, 2, 2), 2),
                         (date(2017, 1, 13), 1.2))
        ])


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
            for x in ("D", "E")
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

    def test_new_price_changes_rebalance_transactions(self):
        trans = TransactionBuilder()()
        date_ = trans.get_date()
        assert len(trans.get_movements()) == 2
        assert sum(x.get_money().get_value(date_) for x in trans.get_movements()) == 0

        curr = trans.get_movements()[0].get_money().currency
        price_change_date = date_ - timedelta(days=1)
        curr.new_price_change(price_change_date, 9283)

        # New movement should have been created
        assert len(trans.get_movements()) == 3
        # must be balanced
        assert sum(x.get_money().get_value(date_) for x in trans.get_movements()) == 0


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


class TestCurrencyPriceChange(CurrencyModelTestCase):

    def setUp(self):
        super().setUp()
        self.set_up_price_changes()
        self.moneys = v(Money(100, self.currency), Money(-100, self.currency))
        self.movs_specs = pvector(
            MovementSpec(a, m) for a, m in zip(self.accs, self.moneys)
        )

    def make_trans_at(self, dt):
        return TransactionFactory()("_", dt, self.movs_specs)

    def test_get_future_price_changes_none(self):
        assert pvector(self.price_changes[-1].get_future_price_changes()) == v()

    def test_get_future_price_changes_three(self):
        assert pvector(self.price_changes[0].get_future_price_changes()) ==\
            self.price_changes[1:]

    def test_get_affected_transactions_none(self):
        for x in self.price_changes:
            assert pvector(x.get_affected_transactions()) == v()

    def test_get_affected_transactions_one(self):
        trans = self.make_trans_at(self.price_changes[0].date)
        assert pvector(self.price_changes[0].get_affected_transactions()) ==\
            v(trans)
        assert pvector(self.price_changes[1].get_affected_transactions()) == v()

    def test_get_affected_transactions_leave_out_if_not_same_cur(self):
        other_cur = CurrencyFactory()("C", 12)
        moneys = v(Money(100, other_cur), Money(-100, other_cur))
        movs_specs = pvector(MovementSpec(a, m) for a, m in zip(self.accs, moneys))
        TransactionFactory()("_", self.price_changes[-1].date, movs_specs)
        for price_change in self.price_changes:
            assert pvector(price_change.get_affected_transactions()) == v()

    def test_has_next_price_change_true(self):
        assert self.price_changes[0].has_next_price_change()

    def test_has_next_price_change_false(self):
        assert not self.price_changes[-1].has_next_price_change()

    def test_has_next_price_change_multiple_currencies(self):
        other_cur = CurrencyBuilder()()
        price_change_another_cur = other_cur.new_price_change(
            date(2100, 1, 1),
            2
        )

        assert price_change_another_cur.get_date() > \
            self.price_changes[-1].get_date()
        assert price_change_another_cur.get_currency() !=\
            self.price_changes[-1].get_currency()

        assert not self.price_changes[-1].has_next_price_change()

from decimal import Decimal
from pyrsistent import v, freeze, pvector
from django.core.exceptions import ValidationError
from common.models import list_to_queryset
from common.test import TestCase
from common.test_utils import TransactionBuilder, MovementSpecBuilder, CurrencyBuilder
from movements.models import Movement, MovementSpec, TransactionFactory, Transaction
from accounts.models import AccountFactory, AccTypeEnum, get_root_acc
from accounts.management.commands.populate_accounts import (
    account_populator,
    account_type_populator
)
from currencies.models import Currency
from currencies.money import Money
from currencies.management.commands.populate_currencies import currency_populator
from datetime import date, timedelta


class MovementsModelsTestCase(TestCase):

    def setUp(self):
        super().setUp()
        currency_populator()
        account_type_populator()
        account_populator()
        self.euro = Currency.objects.get(name="Euro")
        self.real = Currency.objects.get(name="Real")

    def build_two_movement_specs(self, quantity, currencies, date_):
        """ Returns two movement specs whose values sum up to 0 """
        mov_spec_builder = MovementSpecBuilder()
        mov_specs = v(mov_spec_builder(money=Money(quantity, currencies[0])))
        return mov_specs.append(mov_spec_builder(
                money=mov_specs[0].money.convert(currencies[1], date_).revert()
            )
        )


class TestTransactionQueryset_filter_affected_by_price_change(
        MovementsModelsTestCase
):

    def setUp(self):
        super().setUp()
        self.date = date(2017, 2, 3)
        self.new_price = Decimal('1.2')
        self.currency = self.euro
        self.price_change = self.euro.new_price_change(self.date, self.new_price)

        self.mov_spec_builder = MovementSpecBuilder()
        self.trans_builder = TransactionBuilder()

    def test_empty(self):
        empty_qset = Transaction.objects.none()
        assert list(empty_qset.filter_affected_by_price_change(self.price_change))\
            == list(empty_qset)

    def test_transactions_before_date_not_affected(self):
        date_ = self.date - timedelta(days=1)
        mov_specs = self.build_two_movement_specs(
            100,
            (self.currency, self.real),
            date_
        )
        trans = TransactionBuilder()(movements_specs=mov_specs, date_=date_)

        res = Transaction.objects.filter_affected_by_price_change(self.price_change)
        assert trans not in res

    def test_transaction_at_date_shows_up(self):
        date_ = self.date + timedelta(days=1)
        mov_specs = self.build_two_movement_specs(
            250,
            (self.real, self.currency),
            date_
        )
        trans = TransactionBuilder()(movements_specs=mov_specs)

        res = Transaction.objects.filter_affected_by_price_change(self.price_change)
        assert trans in res

    def test_transaction_with_single_currency_not_affected(self):
        mov_specs = self.build_two_movement_specs(
            100,
            (self.real, self.real),
            self.date
        )
        trans = TransactionBuilder()(movements_specs=mov_specs)
        assert len(set(x.get_money().currency for x in trans.get_movements())) == 1

        res = Transaction.objects.filter_affected_by_price_change(self.price_change)
        assert trans not in res

    def test_transactions_at_same_day_affected(self):
        mov_specs = self.build_two_movement_specs(
            120,
            (self.real, self.euro),
            self.date
        )
        trans = TransactionBuilder()(movements_specs=mov_specs, date_=self.date)

        res = Transaction.objects.filter_affected_by_price_change(self.price_change)
        assert trans in res

    def test_not_affected_if_has_future_price_change(self):
        future_date = self.date + timedelta(days=2)
        trans = TransactionBuilder()(date_=future_date)
        new_price_change = trans\
            .get_movements()[0]\
            .get_money()\
            .currency\
            .new_price_change(future_date, Decimal(2))

        res = Transaction.objects.filter_affected_by_price_change(self.price_change)
        assert trans not in res

        res = Transaction.objects.filter_affected_by_price_change(new_price_change)
        assert trans in res


class TestTransactionQueryset_filter_more_than_one_currency(
        MovementsModelsTestCase
):

    def test_contains(self):
        mov_specs = self.build_two_movement_specs(
            150,
            (self.euro, self.real),
            date(2018, 1, 1)
        )
        trans = TransactionBuilder()(movements_specs=mov_specs)
        res = list_to_queryset([trans]).filter_more_than_one_currency()
        assert list(res) == [trans]

    def test_does_not_contains(self):
        mov_specs = self.build_two_movement_specs(
            120,
            (self.real, self.real),
            date(1027, 1, 1)
        )
        trans = TransactionBuilder()(movements_specs=mov_specs)
        res = list_to_queryset([trans]).filter_more_than_one_currency()
        assert list(res) == []


class TestTransactionQueryset_filter_by_currency(MovementsModelsTestCase):

    def test_true(self):
        mov_specs = self.build_two_movement_specs(
            150,
            (self.euro, self.real),
            date(2018, 1, 1)
        )
        trans = TransactionBuilder()(movements_specs=mov_specs)
        assert list(list_to_queryset([trans]).filter_by_currency(self.euro)) ==\
            [trans]
        assert list(list_to_queryset([trans]).filter_by_currency(self.real)) ==\
            [trans]
        other_cur = CurrencyBuilder()()
        assert list(list_to_queryset([trans]).filter_by_currency(other_cur)) ==\
            list()


class TestTransactionFactory(MovementsModelsTestCase):

    def setUp(self):
        super().setUp()
        self.date_ = date(2017, 12, 24)
        self.accs = freeze([
            AccountFactory()("A", AccTypeEnum.LEAF, get_root_acc()),
            AccountFactory()("B", AccTypeEnum.LEAF, get_root_acc())
        ])
        # Force second money to exactly offset the first.
        self.moneys = freeze([
            Money(100, self.euro),
            Money(100, self.euro).convert(self.real, self.date_).revert()
        ])
        self.data = freeze({
            "description": "Hola",
            "date_": self.date_,
            "movements_specs": [
                MovementSpec(a, m) for a, m in zip(self.accs, self.moneys)
            ]
        })

    def data_update(self, **kwargs):
        self.data = self.data.update(kwargs)

    def call(self):
        return TransactionFactory()(**self.data)

    def test_base(self):
        trans = self.call()
        assert trans.get_date() == self.data['date_']
        assert trans.get_description() == self.data['description']
        movements = pvector(trans.get_movements().order_by('account__name'))
        for mov, mov_spec in zip(movements, self.data['movements_specs']):
            assert mov.get_account() == mov_spec.account
            assert mov.get_transaction() == trans
            assert mov.get_date() == trans.get_date()
            assert mov.get_money() == mov_spec.money

    def test_fails_if_movements_values_dont_sum_to_zero(self):
        self.data_update(movements_specs=v(
            MovementSpec(self.accs[0], Money(100, self.euro)),
            MovementSpec(self.accs[1], Money(-99, self.euro))
        ))
        errmsg = Transaction.ERR_MSGS['UNBALANCED_MOVEMENTS']
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()

    def test_fails_if_movements_have_a_single_acc(self):
        self.data_update(movements_specs=v(
            MovementSpec(self.accs[0], Money(100, self.euro)),
            MovementSpec(self.accs[0], Money(-100, self.euro))
        ))
        errmsg = Transaction.ERR_MSGS['SINGLE_ACCOUNT']
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()


class TestMovementModel(MovementsModelsTestCase):

    def test_get_money(self):
        quantity, currency = Decimal(25), self.euro
        mov = Movement(quantity=quantity, currency=currency)
        assert mov.get_money() == Money(quantity, currency)

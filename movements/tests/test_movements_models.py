from decimal import Decimal
from pyrsistent import v, freeze, pvector
from django.core.exceptions import ValidationError
from common.models import list_to_queryset
from common.test import TestCase
from common.test_utils import (
    TransactionBuilder,
    MovementSpecBuilder,
    CurrencyBuilder,
    AccountBuilder
)
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
        """ Returns two movement specs"""
        mov_spec_builder = MovementSpecBuilder()
        return v(
            mov_spec_builder(money=Money(quantity, currencies[0])),
            mov_spec_builder(money=Money(-quantity, currencies[1]))
        )


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
            Money(-100, self.euro)
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

    def test_fails_if_movements_have_a_single_acc(self):
        self.data_update(movements_specs=v(
            MovementSpec(self.accs[0], Money(100, self.euro)),
            MovementSpec(self.accs[0], Money(-100, self.euro))
        ))
        errmsg = Transaction.ERR_MSGS['SINGLE_ACCOUNT']
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()

    def test_fails_on_unbalanced_movements_and_single_account(self):
        self.data_update(movements_specs=v(
            MovementSpec(self.accs[0], Money(100, self.euro)),
            MovementSpec(self.accs[1], Money(-99, self.euro))
        ))
        errmsg = Transaction.ERR_MSGS['UNBALANCED_SINGLE_CURRENCY']
        self.assertRaisesMessage(
            ValidationError,
            errmsg,
            self.call
        )


class TestTransactionModel(MovementsModelsTestCase):

    def test_set_movements_base(self):
        cur = CurrencyBuilder()()
        acc_builder = AccountBuilder()
        values = ((Decimal(1) / Decimal(3)), (Decimal(2) / Decimal(3)), Decimal(-1))
        moneys = [Money(val, cur) for val in values]
        accs = (acc_builder(), acc_builder(), acc_builder())
        mov_specs = [MovementSpec(acc, money) for acc, money in zip(accs, moneys)]
        trans = TransactionBuilder()()
        trans.set_movements(mov_specs)
        assert len(trans.get_movements()) == 3
        movs = trans.get_movements()
        assert list(x.get_money() for x in movs) == \
            list(x.money for x in mov_specs)
        assert list(x.get_account() for x in movs) == \
            list(x.account for x in mov_specs)


class TestMovementModel(MovementsModelsTestCase):

    def test_get_money(self):
        quantity, currency = Decimal(25), self.euro
        mov = Movement(quantity=quantity, currency=currency)
        assert mov.get_money() == Money(quantity, currency)

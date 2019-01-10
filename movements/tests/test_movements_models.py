from datetime import date
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from accounts.management.commands.populate_accounts import (account_populator,
                                                            account_type_populator)
from accounts.models import AccountFactory, AccTypeEnum, get_root_acc
from accounts.tests.factories import AccountTestFactory
from common.test import PacsTestCase
from currencies.management.commands.populate_currencies import \
    currency_populator
from currencies.money import Money
from currencies.tests.factories import CurrencyTestFactory
from movements.models import (Movement, MovementSpec, Transaction,
                              TransactionFactory)

from .factories import TransactionTestFactory


class MovementsModelsTestCase(PacsTestCase):

    def setUp(self):
        super().setUp()
        currency_populator()
        account_type_populator()
        account_populator()


class TestTransactionQueryset_filter_by_account(MovementsModelsTestCase):

    def test_base(self):
        currency = CurrencyTestFactory()
        account = AccountTestFactory()
        other_acc = AccountTestFactory()
        transaction_with = TransactionTestFactory(movements_specs=[
            MovementSpec(account, Money('10', currency)),
            MovementSpec(other_acc, Money('-10', currency)),
        ])
        transaction_without = TransactionTestFactory.create()
        assert list(Transaction.objects.filter_by_account(account)) ==\
            [transaction_with]


class TestTransactionFactory(MovementsModelsTestCase):

    def setUp(self):
        super().setUp()
        self.date_ = date(2017, 12, 24)
        self.accs = [
            AccountFactory()("A", AccTypeEnum.LEAF, get_root_acc()),
            AccountFactory()("B", AccTypeEnum.LEAF, get_root_acc())
        ]
        # Force second money to exactly offset the first.
        self.cur = CurrencyTestFactory()
        self.moneys = [
            Money(100, self.cur),
            Money(-100, self.cur)
        ]
        self.data = {
            "description": "Hola",
            "date_": self.date_,
            "movements_specs": [
                MovementSpec(a, m) for a, m in zip(self.accs, self.moneys)
            ]
        }

    def data_update(self, **kwargs):
        self.data = {**self.data, **kwargs}

    def call(self):
        return TransactionFactory()(**self.data)

    def test_base(self):
        trans = self.call()
        assert trans.get_date() == self.data['date_']
        assert trans.get_description() == self.data['description']
        assert trans.get_movements_specs() == self.data['movements_specs']

    def test_fails_if_movements_have_a_single_acc(self):
        self.data_update(movements_specs=[
            MovementSpec(self.accs[0], Money(100, self.cur)),
            MovementSpec(self.accs[0], Money(-100, self.cur))
        ])
        errmsg = Transaction.ERR_MSGS['SINGLE_ACCOUNT']
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()

    def test_fails_on_unbalanced_movements_and_single_account(self):
        self.data_update(movements_specs=[
            MovementSpec(self.accs[0], Money(100, self.cur)),
            MovementSpec(self.accs[1], Money(-99, self.cur))
        ])
        errmsg = Transaction.ERR_MSGS['UNBALANCED_SINGLE_CURRENCY']
        self.assertRaisesMessage(
            ValidationError,
            errmsg,
            self.call
        )


class TestTransactionModel(MovementsModelsTestCase):

    def test_set_movements_base(self):
        cur = CurrencyTestFactory()
        values = ((Decimal(1) / Decimal(3)), (Decimal(2) / Decimal(3)), Decimal(-1))
        moneys = [Money(val, cur) for val in values]
        accs = AccountTestFactory.create_batch(3)
        mov_specs = [MovementSpec(acc, money) for acc, money in zip(accs, moneys)]
        trans = TransactionTestFactory()
        assert trans.get_movements_specs() != mov_specs
        trans.set_movements(mov_specs)
        assert trans.get_movements_specs() == mov_specs


class TestMovementSpec(MovementsModelsTestCase):

    def test_from_movement(self):
        transactions = TransactionTestFactory()
        mov = transactions.movement_set.all()[0]
        assert MovementSpec.from_movement(mov) == \
            MovementSpec(mov.get_account(), mov.get_money())


class TestMovementModel(MovementsModelsTestCase):

    def test_get_money(self):
        quantity = Decimal(25)
        currency = CurrencyTestFactory()
        mov = Movement(quantity=quantity, currency=currency)
        assert mov.get_money() == Money(quantity, currency)

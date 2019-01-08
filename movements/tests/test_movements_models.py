# !!!! TODO -> isort entire app
from decimal import Decimal
from pyrsistent import v, freeze, pvector

from rest_framework.exceptions import ValidationError

from common.models import list_to_queryset
from common.test import PacsTestCase
from movements.models import (
    Movement, MovementSpec, TransactionFactory, Transaction
)
from accounting.balance import Balance
from accounts.models import AccountFactory, AccTypeEnum, get_root_acc
from accounts.management.commands.populate_accounts import (
    account_populator,
    account_type_populator
)
from accounts.tests.factories import AccountTestFactory
from accounting.money import Money
from currencies.management.commands.populate_currencies import currency_populator
from currencies.tests.factories import CurrencyTestFactory, MoneyTestFactory
from .factories import (
    MovementTestFactory, MovementSpecTestFactory, TransactionTestFactory
)
from datetime import date


class MovementsModelsTestCase(PacsTestCase):

    def setUp(self):
        super().setUp()
        currency_populator()
        account_type_populator()
        account_populator()


class TestTransactionQueryset_filter_more_than_one_currency(
        MovementsModelsTestCase
):

    def test_contains(self):
        mov_specs = freeze(MovementSpecTestFactory.create_batch(2))
        assert len(set(x.money.currency for x in mov_specs)) > 1
        trans = TransactionTestFactory(movements_specs=mov_specs)
        res = list_to_queryset([trans]).filter_more_than_one_currency()
        assert list(res) == [trans]

    def test_does_not_contains(self):
        cur = CurrencyTestFactory()
        moneys = v(MoneyTestFactory(currency=cur))
        moneys = moneys.append(
            MoneyTestFactory(quantity=-moneys[0].quantity, currency=cur)
        )
        mov_specs = pvector(MovementSpecTestFactory(money=m) for m in moneys)
        assert len(set(x.money.currency for x in mov_specs)) == 1
        trans = TransactionTestFactory(movements_specs=mov_specs)
        res = list_to_queryset([trans]).filter_more_than_one_currency()
        assert list(res) == []


class TestTransactionQueryset_filter_by_currency(MovementsModelsTestCase):

    def test_true(self):
        curs = CurrencyTestFactory.create_batch(2)
        moneys = pvector(MoneyTestFactory(currency=c) for c in curs)
        mov_specs = pvector(MovementSpecTestFactory(money=m) for m in moneys)
        trans = TransactionTestFactory(movements_specs=mov_specs)
        assert list(list_to_queryset([trans]).filter_by_currency(curs[0])) ==\
            [trans]
        assert list(list_to_queryset([trans]).filter_by_currency(curs[1])) ==\
            [trans]
        other_cur = CurrencyTestFactory()
        assert list(list_to_queryset([trans]).filter_by_currency(other_cur)) ==\
            list()


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
        self.accs = freeze([
            AccountFactory()("A", AccTypeEnum.LEAF, get_root_acc()),
            AccountFactory()("B", AccTypeEnum.LEAF, get_root_acc())
        ])
        # Force second money to exactly offset the first.
        self.cur = CurrencyTestFactory()
        self.moneys = freeze([
            Money(100, self.cur),
            Money(-100, self.cur)
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
        assert trans.get_movements_specs() == self.data['movements_specs']

    def test_fails_if_movements_have_a_single_acc(self):
        self.data_update(movements_specs=v(
            MovementSpec(self.accs[0], Money(100, self.cur)),
            MovementSpec(self.accs[0], Money(-100, self.cur))
        ))
        errmsg = Transaction.ERR_MSGS['SINGLE_ACCOUNT']
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()

    def test_fails_on_unbalanced_movements_and_single_account(self):
        self.data_update(movements_specs=v(
            MovementSpec(self.accs[0], Money(100, self.cur)),
            MovementSpec(self.accs[1], Money(-99, self.cur))
        ))
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


class TestMovementQuerySet_get_balance(MovementsModelsTestCase):

    def test_no_movements(self):
        qset = Movement.objects.filter(pk=1, id=2)
        assert qset.get_balance() == Balance([])

    def test_single_currency(self):
        currency = CurrencyTestFactory()
        movements_qset = MovementTestFactory.create_batch_qset(3, currency=currency)
        exp = Balance([Money(
            quantity=sum(m.quantity for m in movements_qset),
            currency=currency
        )])
        res = movements_qset.get_balance()
        assert exp == res

    def test_two_currency(self):
        currencies = CurrencyTestFactory.create_batch(2)
        movements = [
            element
            for list_ in [
                MovementTestFactory.create_batch_qset(2, currency=c)
                for c in currencies
            ]
            for element in list_
        ]
        movements_qset = list_to_queryset(movements)
        exp = Balance([
            Money(
                quantity=sum(
                    m.quantity for m in movements_qset
                    if m.currency == c
                ),
                currency=c
            )
            for c in currencies
        ])
        res = movements_qset.get_balance()
        assert exp == res


class TestMovementQuerySet_get_balance_evolution(MovementsModelsTestCase):

    def test_no_movements(self):
        qset = Movement.objects.filter(pk=1, id=2)
        assert qset.get_balance_evolution() == []

    def test_one_movement(self):
        movement = MovementTestFactory()
        qset = list_to_queryset([movement])
        assert qset.get_balance_evolution() == [
            (movement, Balance([]), Balance([movement.get_money()]))
        ]

    def test_one_with_initial_balance_other_currency(self):
        currency = CurrencyTestFactory()
        initial_balance = Balance([Money('123', currency)])
        movement = MovementTestFactory()
        qset = list_to_queryset([movement])
        assert qset.get_balance_evolution(initial_balance) == [
            (
                movement,
                initial_balance,
                initial_balance.add_money(movement.get_money())
            )
        ]

    def test_one_with_initial_balance_same_currency(self):
        currency = CurrencyTestFactory()
        initial_balance = Balance([Money('11.12', currency)])
        movement = MovementTestFactory(currency=currency)
        qset = list_to_queryset([movement])
        assert qset.get_balance_evolution(initial_balance) == [
            (
                movement,
                initial_balance,
                initial_balance.add_money(movement.get_money())
            )
        ]

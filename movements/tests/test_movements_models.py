from datetime import date, timedelta
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from accounts.management.commands.populate_accounts import (account_populator,
                                                            account_type_populator)
from accounts.models import AccountFactory, AccTypeEnum, get_root_acc
from accounts.tests.factories import AccountTestFactory
from common.models import list_to_queryset
from common.test import PacsTestCase, MockQset
from currencies.management.commands.populate_currencies import \
    currency_populator
from currencies.money import Balance, Money
from currencies.tests.factories import CurrencyTestFactory
from movements.models import (Movement, MovementSpec, Transaction,
                              TransactionFactory,
                              TransactionMovementSpecListValidator,
                              TransactionQuerySet)

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


class TestTransactionQueryset_pre_process_for_journal(MovementsModelsTestCase):

    def setUp(self):
        super().setUp()
        self.mock_qset = MockQset()
        self.resp = TransactionQuerySet.pre_process_for_journal(self.mock_qset)

    def test_returns_qset(self):
        assert self.resp is self.mock_qset

    def test_orders_by_date_and_pk(self):
        assert self.mock_qset.order_by_args == ('date', 'pk')

    def test_prefetches_currency_and_account_type(self):
        assert set(self.mock_qset.prefetch_related_args) == set([
            "movement_set__currency",
            "movement_set__account__acc_type"
        ])

    def test_distinct_is_called(self):
        assert self.mock_qset.distinct_called is True


class TestTransactionQueryset_filter_before_transaction(MovementsModelsTestCase):

    def test_none(self):
        transaction = TransactionTestFactory.create()
        qset = Transaction.objects.filter(pk=transaction.pk)
        res = qset.filter_before_transaction(transaction)
        assert list(res) == []

    def test_two_transactions_before_kept(self):
        date_ = date(1988, 2, 23)
        date_before = date_ - timedelta(days=1)
        transaction = TransactionTestFactory.create(date_=date_)
        transactions_before = TransactionTestFactory.create_batch(2, date_=date_before)
        qset = list_to_queryset([transaction, *transactions_before])
        res = qset.filter_before_transaction(transaction)
        assert list(res) == transactions_before

    def test_same_date_pk_higher_filtered(self):
        date_ = date(2001, 11, 1)
        transaction = TransactionTestFactory.create(date_=date_)
        transaction_same_date = TransactionTestFactory(date_=date_)
        assert transaction_same_date.pk > transaction.pk
        res = Transaction.objects.all().filter_before_transaction(transaction)
        assert transaction_same_date not in list(res)

    def test_same_date_pk_lower_kept(self):
        date_ = date(2001, 11, 1)
        transaction_same_date = TransactionTestFactory(date_=date_)
        transaction = TransactionTestFactory.create(date_=date_)
        assert transaction_same_date.pk < transaction.pk
        res = Transaction.objects.all().filter_before_transaction(transaction)
        assert transaction_same_date in list(res)


class TestTransactionQueryset_get_balance_for_account(MovementsModelsTestCase):

    def test_empty_qset(self):
        self.populate_accounts()
        acc = AccountTestFactory()
        qset = Transaction.objects.filter(pk=1, id=2)
        assert qset.get_balance_for_account(acc) == Balance([])

    def test_one_long(self):
        self.populate_accounts()
        transaction = TransactionTestFactory.create()
        account = transaction.get_movements_specs()[0].account
        qset = Transaction.objects.filter(pk=transaction.pk)
        assert qset.get_balance_for_account(account) ==\
            transaction.get_balance_for_account(account)

    def test_two_long(self):
        self.populate_accounts()
        account = AccountTestFactory()
        transactions = TransactionTestFactory.create_batch(
            2,
            movements_specs__1__account=account
        )
        qset = list_to_queryset(transactions)

        resp = qset.get_balance_for_account(account)
        exp = Balance([])
        for t in transactions:
            exp += t.get_balance_for_account(account)
        assert exp == resp

    def test_empty_for_other_account(self):
        self.populate_accounts()
        other_account = AccountTestFactory()
        transaction = TransactionTestFactory()
        assert other_account not in\
            [x.account for x in transaction.get_movements_specs()]

        qset = Transaction.objects.filter(pk=transaction.pk)

        assert qset.get_balance_for_account(other_account) == Balance([])

    def test_two_long_for_parent_account(self):
        self.populate_accounts()
        parent = AccountTestFactory(acc_type=AccTypeEnum.BRANCH)
        child = AccountTestFactory(parent=parent)
        transactions = TransactionTestFactory.create_batch(
            2,
            movements_specs__0__account=child
        )
        qset = list_to_queryset(transactions)

        assert qset.get_balance_for_account(child) ==\
            qset.get_balance_for_account(parent)

    def test_repeated_currency(self):
        self.populate_accounts()
        account, currency = AccountTestFactory(), CurrencyTestFactory()
        transactions = TransactionTestFactory.create_batch(
            3,
            movements_specs__0__account=account,
            movements_specs__0__money__currency=currency
        )
        qset = list_to_queryset(transactions)

        res = qset.get_balance_for_account(account)
        exp = Balance([])
        for t in transactions:
            exp += t.get_balance_for_account(account)
        assert exp == res


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
        errmsg = TransactionMovementSpecListValidator.ERR_MSGS['SINGLE_ACCOUNT']
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()

    def test_fails_on_unbalanced_movements_and_single_account(self):
        self.data_update(movements_specs=[
            MovementSpec(self.accs[0], Money(100, self.cur)),
            MovementSpec(self.accs[1], Money(-99, self.cur))
        ])
        errmsg = TransactionMovementSpecListValidator\
            .ERR_MSGS['UNBALANCED_SINGLE_CURRENCY']
        self.assertRaisesMessage(
            ValidationError,
            errmsg,
            self.call
        )

    def test_fails_if_duplicated_currency_account_pair(self):
        self.data_update(movements_specs=[
            MovementSpec(self.accs[0], Money(1, self.cur)),
            MovementSpec(self.accs[0], Money(1, self.cur)),
            MovementSpec(self.accs[1], Money(-2, self.cur))
        ])
        errmsg = TransactionMovementSpecListValidator.ERR_MSGS[
            "REPEATED_CURRENCY_ACCOUNT_PAIR"
        ]
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()


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

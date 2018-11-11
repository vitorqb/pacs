from pyrsistent import v, freeze, pvector
from django.core.exceptions import ValidationError
from common.test import TestCase
from movements.models import Movement, MovementSpec, TransactionFactory, Transaction
from accounts.models import AccountFactory, AccTypeEnum, get_root_acc
from accounts.management.commands.populate_accounts import (
    account_populator,
    account_type_populator
)
from currencies.models import Currency
from currencies.money import Money
from currencies.management.commands.populate_currencies import currency_populator
from datetime import date


class MovementsModelsTestCase(TestCase):

    def setUp(self):
        super().setUp()
        currency_populator()
        account_type_populator()
        account_populator()
        self.euro = Currency.objects.get(name="Euro")
        self.real = Currency.objects.get(name="Real")


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
        quantity, currency = 25, self.euro
        mov = Movement(quantity=quantity, currency=currency)
        assert mov.get_money() == Money(quantity, currency)

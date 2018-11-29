from common.test import PacsTestCase

from accounts.management.commands.populate_accounts import (
    account_type_populator,
    account_populator
)
from movements.filters import TransactionFilterSet
from movements.tests.factories import TransactionTestFactory, MovementSpecTestFactory
from movements.models import Transaction
from accounts.tests.factories import AccountTestFactory


class TestTransactionFilterSet(PacsTestCase):

    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()

    def test_filter_by_account_it(self):
        accs = AccountTestFactory.create_batch(2)
        transaction = TransactionTestFactory(movements_specs=[
            MovementSpecTestFactory(account=accs[0]),
            MovementSpecTestFactory(account=accs[1]),
        ])
        other_transactions = TransactionTestFactory.create_batch(2)
        qset = Transaction.objects.all()
        filter_set = TransactionFilterSet({'account_id': accs[0].pk}, qset)
        assert list(filter_set.qs) == [transaction]

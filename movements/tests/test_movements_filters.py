from common.test import PacsTestCase

from accounts.management.commands.populate_accounts import (
    account_type_populator,
    account_populator
)
from movements.filters import TransactionFilterSet
from movements.tests.factories import TransactionTestFactory, MovementSpecTestFactory
from movements.models import Transaction
from accounts.models import AccTypeEnum
from accounts.tests.factories import AccountTestFactory


class TestTransactionFilterSet(PacsTestCase):

    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()

    def test_filter_by_account_id(self):
        accs = AccountTestFactory.create_batch(2)
        transaction = TransactionTestFactory(movements_specs=[
            MovementSpecTestFactory(account=accs[0]),
            MovementSpecTestFactory(account=accs[1]),
        ])
        other_transactions = TransactionTestFactory.create_batch(2)
        qset = Transaction.objects.all()
        filter_set = TransactionFilterSet({'account_id': accs[0].pk}, qset)
        assert list(filter_set.qs) == [transaction]

    def test_filter_by_parent_account_id(self):
        parent = AccountTestFactory(acc_type=AccTypeEnum.BRANCH)
        accs = AccountTestFactory.create_batch(2, parent=parent)
        transaction = TransactionTestFactory(movements_specs=[
            MovementSpecTestFactory(account=accs[0]),
            MovementSpecTestFactory(account=accs[1]),
        ])
        other_transactions = TransactionTestFactory.create_batch(2)
        qset = Transaction.objects.all()
        filter_set = TransactionFilterSet({'account_id': parent.pk}, qset)
        assert list(filter_set.qs) == [transaction]

    def test_count_query_number_for_large_account_hierarchies(self):
        super_parent = AccountTestFactory(acc_type=AccTypeEnum.BRANCH)
        parents = AccountTestFactory.create_batch(
            3,
            acc_type=AccTypeEnum.BRANCH,
            parent=super_parent
        )
        accs = []
        for i in range(3):
            accs += AccountTestFactory.create_batch(
                3,
                acc_type=AccTypeEnum.LEAF,
                parent=parents[i]
            )
        with self.assertNumQueries(2):
            qset = Transaction.objects.all()
            TransactionFilterSet({'account_id': super_parent.id}, qset).qs

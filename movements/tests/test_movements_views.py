from datetime import date

from django.urls import resolve

from rest_framework.exceptions import ValidationError

from common.test import PacsTestCase

from movements.views import TransactionViewSet
from movements.serializers import TransactionSerializer, MovementSpecSerializer
from movements.models import Transaction, MovementSpec
from .factories import TransactionTestFactory, MovementSpecTestFactory
from accounts.tests.factories import AccountTestFactory
from accounts.models import AccountType
from accounts.management.commands.populate_accounts import (
    account_type_populator,
    account_populator
)
from currencies.tests.factories import CurrencyTestFactory
from currencies.money import Money
from currencies.serializers import MoneySerializer


class MovementsViewsTestCase(PacsTestCase):

    def populate_accounts(self):
        account_type_populator()
        account_populator()


class TestTransactionView(MovementsViewsTestCase):

    def setUp(self):
        super().setUp()
        # Some default data for the post request
        self.populate_accounts()
        self.acc_type_leaf = AccountType.objects.get(name="Leaf")
        self.accs = AccountTestFactory.create_batch(2, acc_type=self.acc_type_leaf)
        self.cur = CurrencyTestFactory()
        self.moneys = [Money(200, self.cur), Money(-200, self.cur)]
        self.movements_specs = [
            MovementSpec(self.accs[0], self.moneys[0]),
            MovementSpec(self.accs[1], self.moneys[1])
        ]
        self.post_data = {
            'description': 'A',
            'date': date(2018, 12, 21),
            'movements_specs': [
                MovementSpecSerializer(self.movements_specs[0]).data,
                MovementSpecSerializer(self.movements_specs[1]).data
            ]
        }

    def test_url_resolves_to_view_function(self):
        assert resolve('/transactions/').func.cls == TransactionViewSet

    def test_url_for_specific_transaction_resolves_to_view(self):
        resolver = resolve('/transactions/12/')
        assert resolver.func.cls == TransactionViewSet
        assert resolver.kwargs == {'pk': '12'}

    def test_get_transactions(self):
        self.populate_accounts()
        TransactionTestFactory.create_batch(5)
        assert self.client.get('/transactions/').json() == \
            [TransactionSerializer(x).data for x in Transaction.objects.all()]

    def test_get_single_transaction(self):
        transactions = TransactionTestFactory.create_batch(2)
        assert self.client.get(f'/transactions/{transactions[0].pk}/').json() == \
            TransactionSerializer(transactions[0]).data

    def test_post_single_transaction(self):
        resp = self.client.post('/transactions/', self.post_data)
        assert resp.status_code == 201, resp.data
        assert resp.json()['date'] == '2018-12-21'
        assert resp.json()['description'] == self.post_data['description']

        obj = Transaction.objects.get(pk=resp.json()['pk'])

        assert obj.get_description() == 'A'
        assert obj.date == date(2018, 12, 21)

        assert obj.get_movements() == [
            MovementSpec(self.accs[0], Money(200, self.cur)),
            MovementSpec(self.accs[1], Money(-200, self.cur))
        ]

    def test_post_transaction_with_empty_movements_returns_error(self):
        self.post_data['movements_specs'] = []
        resp = self.client.post('/transactions/', self.post_data)
        assert resp.status_code == 400
        assert 'movements_specs' in resp.json(), resp.json()
        assert Transaction.ERR_MSGS['TWO_OR_MORE_MOVEMENTS'] in \
            resp.json()['movements_specs']

    def test_post_transaction_with_one_single_movements_returns_error(self):
        self.post_data['movements_specs'] = [
            MovementSpecSerializer(MovementSpecTestFactory()).data
        ]
        resp = self.client.post('/transactions/', self.post_data)
        assert resp.status_code == 400
        assert 'movements_specs' in resp.json(), resp.json()
        assert Transaction.ERR_MSGS['TWO_OR_MORE_MOVEMENTS'] in \
            resp.json()['movements_specs']

    def test_post_single_account_raises_err(self):
        acc = AccountTestFactory()
        movements_specs = MovementSpecTestFactory.create_batch(3, account=acc)
        self.post_data['movements_specs'] = [
            MovementSpecSerializer(x).data for x in movements_specs
        ]
        resp = self.client.post('/transactions/', self.post_data)
        assert resp.status_code == 400
        assert 'movements_specs' in resp.json()
        assert Transaction.ERR_MSGS['SINGLE_ACCOUNT'] in \
            resp.json()['movements_specs']

    def test_patch_transaction_with_single_currency_but_unmatched_values_err(self):
        # Same currency, unmatched values!
        trans = TransactionTestFactory()
        moneys = [Money(100, self.cur), Money(-98, self.cur)]
        movements_specs = [MovementSpecTestFactory(money=m) for m in moneys]
        resp = self.client.patch(
            f'/transactions/{trans.pk}/',
            {'movements_specs': [
                MovementSpecSerializer(m).data for m in movements_specs
            ]}
        )
        assert resp.status_code == 400
        assert 'movements_specs' in resp.json()
        assert Transaction.ERR_MSGS['UNBALANCED_SINGLE_CURRENCY'] in \
            resp.json()['movements_specs']

    def test_patch_transaction(self):
        acc_type_leaf = AccountType.objects.get(name="Leaf")
        accs = AccountTestFactory.create_batch(3, acc_type=acc_type_leaf)
        cur = CurrencyTestFactory()
        trans = TransactionTestFactory()
        new_movements = [MovementSpecSerializer(x).data for x in (
            MovementSpec(accs[0], Money(100, cur)),
            MovementSpec(accs[1], Money(50, cur)),
            MovementSpec(accs[2], Money(-150, cur))
        )]
        resp = self.client.patch(
            f'/transactions/{trans.pk}/',
            {'movements_specs': new_movements}
        )
        assert resp.status_code == 200, resp.data
        trans.refresh_from_db()

        movements = trans.get_movements()
        assert len(movements) == 3
        assert [x.money for x in movements] == \
            [Money(100, cur), Money(50, cur), Money(-150, cur)]

    def test_delete_transaction(self):
        trans = TransactionTestFactory()
        trans_pk = trans.pk
        self.client.delete(f'/transactions/{trans.id}/')
        assert trans_pk not in Transaction.objects.all().in_bulk()

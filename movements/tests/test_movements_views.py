from datetime import date

from django.urls import resolve

from common.test import PacsTestCase

from movements.views import TransactionViewSet
from movements.serializers import TransactionSerializer, MovementSpecSerializer
from movements.models import Transaction, MovementSpec
from .factories import TransactionTestFactory
from accounts.tests.factories import AccountTestFactory
from accounts.models import AccountType
from currencies.tests.factories import CurrencyTestFactory
from currencies.money import Money


class MovementsViewsTestCase(PacsTestCase):
    pass


class TestTransactionView(MovementsViewsTestCase):

    def test_url_resolves_to_view_function(self):
        assert resolve('/transactions/').func.cls == TransactionViewSet

    def test_url_for_specific_transaction_resolves_to_view(self):
        resolver = resolve('/transactions/12/')
        assert resolver.func.cls == TransactionViewSet
        assert resolver.kwargs == {'pk': 12}

    def test_get_transactions(self):
        TransactionTestFactory.create_batch(5)
        assert self.client.get('/transactions/').json() == \
            [TransactionSerializer(x).data for x in Transaction.objects.all()]

    def test_get_single_transaction(self):
        transactions = TransactionTestFactory.create_batch(2)
        assert self.client.get(f'/transactions/{transactions[0].pk}/') == \
            TransactionSerializer(transactions[0]).data

    # !!!! TODO -> Add test not allowing creating transactions that are empty
    # !!!! TODO -> Add test not allowing creating transactions that have a single
    # !!!! currency but unmatched values.
    # !!!! TODO -> Add test not allowing creating transactions that have a single
    # !!!! account.
    def test_post_single_transaction(self):
        # !!!! TODO -> Dont hardcode 'Leaf' here. Instead allow passing
        # !!!! AccTypeEnum.LEAF to the factory.
        acc_type_leaf = AccountType.objects.get(name="Leaf")
        accs = AccountTestFactory.create_batch(2, acc_type=acc_type_leaf)
        cur = CurrencyTestFactory()
        data = {
            'description': 'A',
            'date': date(2018, 12, 21),
            'movements_specs': [
                {
                    "account": accs[0].pk,
                    "money": {
                        "quantity": 200,
                        "currency": cur.pk
                    }
                },
                {
                    "account": accs[1].pk,
                    "Money": {
                        "quantity": -200,
                        "currency": cur.pk
                    }
                }
            ]
        }
        resp = self.client.post('/transactions/', data)
        assert resp['date'] == '2018-12-21'
        assert resp['description'] == data['description']

        obj = Transaction.objects.get(pk=resp['pk'])

        assert obj.get_description() == 'A'
        assert obj.date == date(2018, 12, 21)

        movements = obj.get_movements().order_by('-value')
        assert movements[0].get_account() == accs[0]
        assert movements[0].get_money().get_value() == 200
        assert movements[0].get_money().get_currency() == cur
        assert movements[1].get_account() == accs[1]
        assert movements[1].get_money().get_value() == -200
        assert movements[1].get_money().get_currency() == cur

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
            {'movements': new_movements}
        )
        assert resp.status_code == 200, resp.data
        trans.refresh_from_db()

        movements = trans.get_movements().order_by('-value')
        assert len(movements) == 3
        assert [x.get_money() for x in movements] == \
            [Money(100, cur), Money(50, cur), Money(-150, cur)]

    def test_delete_transaction(self):
        trans = TransactionTestFactory()
        trans_pk = trans.pk
        self.client.delete(f'/transactions/{trans.id}/')
        assert trans_pk not in Transaction.objects.all().in_bulk()

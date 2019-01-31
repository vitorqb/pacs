from decimal import Decimal
from unittest.mock import Mock, patch

from django.urls.base import resolve
from rest_framework.test import APIRequestFactory

from accounts.models import Account, AccTypeEnum, get_root_acc
from accounts.serializers import AccountSerializer
from accounts.tests.factories import AccountTestFactory
from accounts.views import AccountViewSet
from common.test import PacsTestCase
from currencies.money import Balance
from currencies.tests.factories import MoneyTestFactory
from movements.models import MovementSpec, Transaction, TransactionQuerySet
from movements.serializers import MovementSpecSerializer
from movements.tests.factories import TransactionTestFactory


class AccountViewTestCase(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.req_fact = APIRequestFactory()


class TestAccountViewset(AccountViewTestCase):

    def setup_data_for_pagination(self):
        self.populate_accounts()
        self.accs = AccountTestFactory.create_batch(2)
        self.movements_specs = [
            [
                MovementSpec(self.accs[0], MoneyTestFactory()),
                MovementSpec(self.accs[1], MoneyTestFactory())
            ],
            [
                MovementSpec(self.accs[0], MoneyTestFactory()),
                MovementSpec(self.accs[1], MoneyTestFactory())
            ]
        ]
        self.transactions = [
            TransactionTestFactory(movements_specs=m) for m in self.movements_specs
        ]
        self.transactions.sort(key=lambda x: x.date)

    def test_url_resolves_to_view_function(self):
        func = resolve('/accounts/').func
        assert func.cls == AccountViewSet

    def test_url_for_specific_account_resolves_to_view_func(self):
        resolver = resolve('/accounts/1/')
        assert resolver.func.cls == AccountViewSet
        assert resolver.kwargs == {'pk': '1'}

    def test_get_count_queries(self):
        self.populate_accounts()
        top_accs = AccountTestFactory.create_batch(2, acc_type=AccTypeEnum.BRANCH)
        lower_accs = [          # noqa
            *AccountTestFactory.create_batch(
                3,
                parent=top_accs[0],
                acc_type=AccTypeEnum.BRANCH
            ),
            *AccountTestFactory.create_batch(
                2,
                parent=top_accs[1],
                acc_type=AccTypeEnum.BRANCH
            ),
        ]
        last_accs = [          # noqa
            *AccountTestFactory.create_batch(
                3,
                parent=lower_accs[0],
                acc_type=AccTypeEnum.LEAF
            ),
            *AccountTestFactory.create_batch(
                2,
                parent=lower_accs[2],
                acc_type=AccTypeEnum.LEAF
            ),
        ]
        with self.assertNumQueries(2):
            self.client.get('/accounts/')

    def test_get_for_list_of_accounts(self):
        self.populate_accounts()
        AccountTestFactory.create_batch(3)
        accs = list(Account.objects.all())

        request = self.req_fact.get('/accounts/')
        resp = resolve('/accounts/').func(request)
        self.assertEqual(
            AccountSerializer(accs, many=True).data,
            resp.data
        )

    def test_get_for_single_account(self):
        self.populate_accounts()
        acc = AccountTestFactory()

        resp = self.client.get(f'/accounts/{acc.pk}/')
        self.assertEqual(
            AccountSerializer(acc).data,
            resp.json()
        )

    def test_post_for_new_account(self):
        self.populate_accounts()
        root_acc = get_root_acc()
        acc_data = {
            "name": "MyAcc",
            "acc_type": "Branch",
            "parent": root_acc.pk
        }
        request = self.req_fact.post(f'/accounts/', acc_data)
        resp = resolve(f'/accounts/').func(request)
        assert resp.status_code == 201, resp.data
        assert Account.objects.filter(name="MyAcc").exists()

    def test_post_for_new_account_with_wrong_name(self):
        self.populate_accounts()
        # Notice that we are sending accType and not acc_type
        acc_data = {"name": "MyAcc", "accType": "Leaf", "parent": 1}
        resp = self.client.post("/accounts/", acc_data)
        assert resp.status_code == 400
        assert "acc_type" in resp.json()

    def test_patch_account(self):
        self.populate_accounts()
        acc = AccountTestFactory()
        new_name = "New Name"
        assert acc.get_name() != new_name

        url = f'/accounts/{acc.pk}/'
        resp = self.client.patch(url, {'name': new_name}, format="json")
        assert resp.status_code == 200, resp.data
        acc.refresh_from_db()
        assert acc.get_name() == new_name

    def test_patch_account_type_raises_error(self):
        self.populate_accounts()
        acc = AccountTestFactory(acc_type=AccTypeEnum.BRANCH)
        new_type = AccTypeEnum.LEAF.value
        resp = self.client.patch(
            f"/accounts/{acc.pk}/",
            {'acc_type': new_type},
        )
        assert resp.status_code == 400
        assert len(resp.data) == 1
        assert "acc_type" in resp.data

    def test_delete_account(self):
        self.populate_accounts()
        acc = AccountTestFactory()
        assert Account.objects.filter(name=acc.get_name()).exists()
        resp = self.client.delete(f'/accounts/{acc.pk}/')
        assert resp.status_code == 204
        assert not Account.objects.filter(name=acc.get_name()).exists()

    @patch("accounts.views.get_journal_paginator")
    @patch("accounts.views.Journal")
    @patch.object(TransactionQuerySet, "pre_process_for_journal")
    def test_get_journal(
            self,
            m_TransactionQuerySet_pre_process_for_journal,
            m_Journal,
            m_get_journal_paginator
    ):
        # To avoid django rest bug
        self.populate_accounts()
        account = AccountTestFactory()
        m_paginator = m_get_journal_paginator.return_value
        m_paginator.get_data.return_value = {"some": "unique value"}

        resp = self.client.get(f"/accounts/{account.pk}/journal/")

        m_Journal.assert_called_with(
            account,
            Balance([]),
            m_TransactionQuerySet_pre_process_for_journal()
        )

        # Called m_get_journal_paginator with Journal
        assert m_get_journal_paginator.call_count == 1
        assert m_get_journal_paginator.call_args[0][1] == m_Journal()

        # Returned what the paginator returns
        assert resp.json() == m_paginator.get_data.return_value

    def test_get_journal_paginated_defaults_to_first_page(self):
        """ Sending `page_size` with no `page` should be the same as
        sending `page=1` """
        self.setup_data_for_pagination()
        page, page_size = 1, 1
        # With page=1
        resp_with_page = self.client.get(
            f"/accounts/{self.accs[0].pk}/journal/?page={page}&page_size={page_size}"
        )
        # Without page
        resp_no_page = self.client.get(
            f"/accounts/{self.accs[0].pk}/journal/?page_size={page_size}"
        )
        assert resp_with_page.json() == resp_no_page.json()

    def test_get_journal_paginated_first_page(self):
        self.setup_data_for_pagination()
        page, page_size = 1, 1
        resp = self.client.get(
            f"/accounts/{self.accs[0].pk}/journal/?page={page}&page_size={page_size}"
        )
        # We are querying the first of two transactions.
        assert resp.json()['previous'] is None
        assert resp.json()['count'] == len(self.transactions)
        assert resp.json()['next'] is not None

        assert resp.json()['journal']['account'] == self.accs[0].pk

        assert len(resp.json()['journal']['transactions']) == 1
        assert resp.json()['journal']['transactions'][0]['pk'] == \
            self.transactions[0].pk

        assert len(resp.json()['journal']['balances']) == 1
        movements_specs = self.transactions[0].get_movements_specs()
        assert Decimal(resp.json()['journal']['balances'][0][0]['quantity']) == \
            movements_specs[0].money.quantity

    def test_get_journal_paginated_second_page(self):
        self.setup_data_for_pagination()
        page, page_size = 1, 1
        next_ = self.client.get(
            f"/accounts/{self.accs[0].pk}/journal/?page={page}&page_size={page_size}"
        ).json()['next']
        resp = self.client.get(next_)
        # We have 2 transactions, and we are getting 1, so this should be the last
        assert resp.json()['previous'] is not None
        assert resp.json()['count'] == len(self.transactions)
        assert resp.json()['next'] is None

        assert resp.json()['journal']['account'] == self.accs[0].pk

        assert len(resp.json()['journal']['transactions']) == 1
        # We are querying for the second transaction
        assert resp.json()['journal']['transactions'][0]['pk'] == \
            self.transactions[1].pk

        assert len(resp.json()['journal']['balances']) == 1
        movement_specs = self.transactions[1].get_movements_specs()
        assert resp.json()['journal']['balances'][0] == \
            [MovementSpecSerializer(movement_specs[0]).data['money']]

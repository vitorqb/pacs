from django.urls.base import resolve

from unittest.mock import patch

from rest_framework.test import APIRequestFactory

from common.test import PacsTestCase
from accounts.models import Account, get_root_acc, AccTypeEnum
from accounts.serializers import AccountSerializer
from accounts.views import AccountViewSet
from accounts.tests.factories import AccountTestFactory
from accounts.management.commands.populate_accounts import account_populator, account_type_populator

from movements.models import Transaction
from accounting.balance import Balance


class AccountViewTestCase(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.req_fact = APIRequestFactory()

    def populate_accounts(self):
        """ Populates db with Accounts """
        account_type_populator()
        account_populator()


class TestAccountViewset(AccountViewTestCase):

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

    @patch("accounts.views.JournalSerializer")
    @patch("accounts.views.Journal")
    @patch.object(Transaction, "objects")
    def test_get_journal(
            self,
            m_Transaction_objects,
            m_Journal,
            m_JournalSerializer
    ):
        self.populate_accounts()
        account = AccountTestFactory()
        m_JournalSerializer.return_value.data = {"some": "unique value"}

        resp = self.client.get(f"/accounts/{account.pk}/journal/")

        m_qset = Transaction.objects.prefetch_related(
            "movement_set__currency",
            "movement_set__account__acc_type"
        )
        m_Journal.assert_called_with(
            account,
            Balance([]),
            m_qset.order_by('date').filter_by_account(account)
        )
        m_JournalSerializer.assert_called_with(m_Journal())
        assert resp.json() == m_JournalSerializer().data

import os
import requests
from datetime import date

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from accounts.management.commands.populate_accounts import (
    account_type_populator,
    account_populator,
    ACCOUNT_DATA
)
from accounts.tests.factories import AccountTestFactory
from accounts.models import AccTypeEnum, get_root_acc, AccountType
from currencies.management.commands.populate_currencies import (
    currency_populator,
    CURRENCIES_DATA
)
from currencies.tests.factories import CurrencyTestFactory
from currencies.money import Money
from movements.tests.factories import TransactionTestFactory
from movements.models import MovementSpec
from movements.serializers import TransactionSerializer


# !!!! TODO -> adapt tests to staging server?
class FunctionalTests(StaticLiveServerTestCase):

    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()
        currency_populator()

        # If there is a PACS_STAGING_SERVER, use
        staging_server_url = os.environ.get('PACS_STAGING_SERVER')
        if staging_server_url:
            self.live_server_url = staging_server_url

    def assert_response_status_okay(self, resp):
        """ Asserts that a Response has a 2xx status code """
        assert str(resp.status_code)[0] == "2", \
            f"Response for {resp.url} had status code " +\
            f"{resp.status_code} and not 2xx. \nContent: {resp.content}"

    def get_json(self, url):
        """
        Makes a get request, ensures that it returns 2**, and parses the json
        """
        resp = requests.get(f"{self.live_server_url}{url}")
        self.assert_response_status_okay(resp)
        return resp.json()

    def post_json(self, url, json={}):
        """ Makes a json request, ensures it returns 2**, and parses the json """
        resp = requests.post(f"{self.live_server_url}{url}", json=json)
        self.assert_response_status_okay(resp)
        return resp.json()

    def patch_json(self, url, json={}):
        """ Makes a json request, ensures it returns 2**, and parses the json """
        resp = requests.patch(f"{self.live_server_url}{url}", json=json)
        self.assert_response_status_okay(resp)
        return resp.json()

    def assert_is_acc_name(self, name):
        """ Asserts that name is an acc name returned by a get request """
        accs = self.get_json('/accounts/')
        assert any(x['name'] == name for x in accs), \
            f"'{name}' not found on account names '{accs}'"

    def assert_is_not_acc_name(self, name):
        """ Asserts that name is not an acc name returned by a get request """
        accs = self.get_json('/accounts/')
        assert all(x['name'] != name for x in accs), \
            f"'{name}' found on account names '{accs}'"

    def test_unlogged_user_cant_make_queries(self):
        # The user tries to make a query without the header and sees 403
        url = f'{self.live_server_url}/accounts/'
        assert requests.get(url).status_code == 403,\
            "User should have been unauthorized because of no header!"

        # Then he puts the correct token and it works!
        headers = {'Authentication': f'Token {settings.ADMINT_TOKEN}'}
        assert requests.get(url, headers=headers).status_code == 200, \
            "User should have been successfull becase he has the header"

    def test_creates_an_account_hierarchy(self):
        # The user enters and only sees the default accounts there
        resp_accs = self.get_json('/accounts/')
        assert len(resp_accs) == len(ACCOUNT_DATA)
        assert set(x['name'] for x in resp_accs) == \
            set(x['name'] for x in ACCOUNT_DATA)

        # The user decides to add Expenses and Supermarket
        root_acc_pk = next(x['pk'] for x in resp_accs if x['acc_type'] == 'Root')
        expenses_acc = {
            "name": "Expenses",
            "acc_type": "Branch",
            "parent": root_acc_pk
        }
        expenses_json = self.post_json("/accounts/", expenses_acc)

        expenses_pk = expenses_json['pk']
        supermarket_acc = {
            "name": "Supermarket",
            "acc_type": "Leaf",
            "parent": expenses_pk
        }
        resp = self.post_json("/accounts/", supermarket_acc)

        assert resp['parent'] == expenses_pk
        assert resp['acc_type'] == "Leaf"
        assert resp['name'] == "Supermarket"

    def test_user_changes_name_of_account(self):
        # The user had previously creates an account
        orig_name = "Current Account"
        AccountTestFactory(name=orig_name)

        # Which he sees when he opens the app
        accs_json = self.get_json("/accounts/")
        assert orig_name in set(x['name'] for x in accs_json)
        acc_data = next(x for x in accs_json if x['name'] == orig_name)

        # It now decides to change the name
        new_name = "Current Account (La Caixa)"
        self.patch_json(f"/accounts/{acc_data['pk']}/", {"name": new_name})

        # And he sees it worked, and he is happy
        self.assert_is_acc_name(new_name)
        self.assert_is_not_acc_name(orig_name)

    def test_user_changes_account_hierarchy(self):
        # The user had previously created an Current Account whose
        # father was Root Account
        root = get_root_acc()
        cur_acc = AccountTestFactory(
            name="Current Account",
            parent=root,
            acc_type=AccTypeEnum.LEAF
        )

        # Now it wants to have Current Accounts as a child of Root, and
        # two specific accounts for two different Current Accounts
        # .
        # | -- Root Account
        # |    |-- Current Account
        # |    |   |-- Current Account Itau
        # |    |   `-- Current Account LaCaixa

        # It currects the name of the existant account
        self.patch_json(
            f"/accounts/{cur_acc.pk}/",
            {"name": "Current Account Itau"}
        )
        # And sees that it worked
        self.assert_is_acc_name("Current Account Itau")
        self.assert_is_not_acc_name("Current Account")

        # He creates the new father for it
        new_cur_acc_data = {
            "name": "Current Account",
            "parent": root.pk,
            "acc_type": "Branch"
        }
        resp_data = self.post_json("/accounts/", new_cur_acc_data)
        new_cur_acc_pk = resp_data['pk']
        # And sees that it worked
        self.assert_is_acc_name(new_cur_acc_data['name'])

        # He sets the old acc to have this father
        resp_data = self.patch_json(
            f"/accounts/{cur_acc.pk}/",
            json={"parent": new_cur_acc_pk}
        )
        assert resp_data['parent'] == new_cur_acc_pk

        # And creates the new account
        self.post_json(
            "/accounts/",
            json={
                "name": "Current Account LaCaixa",
                "parent": new_cur_acc_pk,
                "acc_type": "Leaf"
            }
        )
        self.assert_is_acc_name("Current Account LaCaixa")

    def test_first_transaction(self):
        # The user creates two accounts
        accs_raw_data = [
            {
                "name": "Salary",
                "acc_type": "Leaf",
                "parent": get_root_acc().pk
            },
            {
                "name": "Money",
                "acc_type": "Leaf",
                "parent": get_root_acc().pk
            }
        ]
        accs = [
            self.post_json("/accounts/", raw_data) for raw_data in accs_raw_data
        ]

        # And the Yen currency
        euro_raw_data = {"name": "Yen"}
        euro = self.post_json("/currencies/", euro_raw_data)

        # And it's first transaction ever!
        trans_raw_data = {
            "description": "Earned some money!",
            "date": "2018-01-01",
            "movements_specs": [
                {
                    "account": accs[0]['pk'],
                    "money": {
                        "quantity": -1000,
                        "currency": euro['pk']
                    }
                },
                {
                    "account": accs[1]['pk'],
                    "money": {
                        "quantity": 1000,
                        "currency": euro['pk']
                    }
                },
            ]
        }
        self.post_json("/transactions/", trans_raw_data)

        # Which now appears when querying for all transactions
        get_trans_resp = self.get_json("/transactions/")
        assert len(get_trans_resp) == 1
        assert get_trans_resp[0]['date'] == trans_raw_data['date']

    def test_check_balance_and_add_transaction(self):
        # The user has two accounts he uses, with two transactions between them
        cur = CurrencyTestFactory()
        accs = AccountTestFactory.create_batch(2, acc_type=AccTypeEnum.LEAF)
        transactions = [
            TransactionTestFactory(
                date_=date(2018, 1, 2),
                movements_specs=[
                    MovementSpec(accs[0], Money(100, cur)),
                    MovementSpec(accs[1], Money(-100, cur))
                ]
            ),
            TransactionTestFactory(
                date_=date(2018, 1, 1),
                movements_specs=[
                    MovementSpec(accs[0], Money(22, cur)),
                    MovementSpec(accs[1], Money(-22, cur))
                ]
            )
        ]
        transactions.sort(key=lambda x: x.get_date(), reverse=True)
        serialized_transactions = \
            TransactionSerializer(transactions, many=True).data

        # He also has another two accounts with an unrelated transaction
        other_accs = AccountTestFactory.create_batch(2, acc_type=AccTypeEnum.LEAF)
        TransactionTestFactory(
            date_=date(2017, 1, 2),
            movements_specs=[
                MovementSpec(other_accs[0], Money(100, cur)),
                MovementSpec(other_accs[1], Money(-100, cur))
            ]
        )

        # He queries ony for transactions involving acc1, and see the
        # same ones listed, in chronological order
        assert self.get_json(f"/transactions/?account_id={accs[0].pk}") == \
            serialized_transactions

        # He adds a new transaction of 10 cur to acc2
        new_transaction = self.post_json(
            f"/transactions/",
            {
                "description": "New Transaction",
                "date": "2018-01-03",
                "movements_specs": [
                    {
                        "account": accs[0].pk,
                        "money": {
                            "quantity": 10,
                            "currency": cur.pk
                        }
                    },
                    {
                        "account": accs[1].pk,
                        "money": {
                            "quantity": -10,
                            "currency": cur.pk
                        }
                    }
                ]
            }
        )
        serialized_transactions.insert(0, new_transaction)

        # He queries again for transactions involving acc1, and see all
        # of them listed
        assert self.get_json(f"/transactions/?account_id={accs[0].pk}") == \
            serialized_transactions

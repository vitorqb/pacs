from datetime import date

import attr
import requests
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from accounts.management.commands.populate_accounts import (ACCOUNT_DATA,
                                                            account_populator,
                                                            account_type_populator)
from accounts.models import AccTypeEnum, get_root_acc
from accounts.tests.factories import AccountTestFactory
from currencies.management.commands.populate_currencies import \
    currency_populator
from currencies.money import Money
from currencies.tests.factories import CurrencyTestFactory
from movements.models import MovementSpec
from movements.serializers import TransactionSerializer
from movements.tests.factories import TransactionTestFactory


class FunctionalTests(StaticLiveServerTestCase):

    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()
        currency_populator()

        # Sets up a request session with authorization header
        self.requests = _TestRequests(
            self.live_server_url,
            {'Authorization': f"Token {settings.ADMIN_TOKEN}"}
        )

    def assert_response_status_okay(self, resp):
        """ Asserts that a Response has a 2xx status code """
        assert str(resp.status_code)[0] == "2", \
            f"Response for {resp.url} had status code " +\
            f"{resp.status_code} and not 2xx. \nContent: {resp.content}"

    def get_json(self, path):
        """
        Makes a get request, ensures that it returns 2**, and parses the json
        """
        resp = self.requests.get(f"{path}")
        self.assert_response_status_okay(resp)
        return resp.json()

    def post_json(self, path, json={}):
        """ Makes a json request, ensures it returns 2**, and parses the json """
        resp = self.requests.post(f"{path}", json=json)
        self.assert_response_status_okay(resp)
        return resp.json()

    def patch_json(self, path, json={}):
        """ Makes a json request, ensures it returns 2**, and parses the json """
        resp = self.requests.patch(f"{path}", json=json)
        self.assert_response_status_okay(resp)
        return resp.json()

    def test_unlogged_user_cant_make_queries(self):
        # The user tries to make a query without the header and sees 403
        self.requests.headers = {}
        assert self.requests.get(URLS.account).status_code == 403,\
            "User should have been unauthorized because of no header!"

        # Then he puts the correct token and it works!
        self.requests.headers = {'Authorization': f'Token {settings.ADMIN_TOKEN}'}
        assert self.requests.get(URLS.account).status_code == 200, \
            "User should have been successfull becase he has the header"

    def test_creates_an_account_hierarchy(self):
        # The user enters and only sees the default accounts there
        resp_accs = self.get_json(URLS.account)
        assert len(resp_accs) == len(ACCOUNT_DATA)
        assert set(x['name'] for x in resp_accs) == \
            set(x['name'] for x in ACCOUNT_DATA)

        # The user decides to add Expenses and Supermarket
        root_acc = _find_root(resp_accs)
        expenses_acc = {
            "name": "Expenses",
            "acc_type": "Branch",
            "parent": root_acc['pk']
        }
        expenses_json = self.post_json(URLS.account, expenses_acc)

        expenses_pk = expenses_json['pk']
        supermarket_acc = {
            "name": "Supermarket",
            "acc_type": "Leaf",
            "parent": expenses_pk
        }
        resp = self.post_json(URLS.account, supermarket_acc)

        assert resp['parent'] == expenses_pk
        assert resp['acc_type'] == "Leaf"
        assert resp['name'] == "Supermarket"

        # And he can see them
        accounts = self.get_json(URLS.account)
        for x in 'Expenses', 'Supermarket':
            _assert_contains(accounts, 'name', x)

    def test_user_changes_name_of_account(self):
        # The user had previously creates an account
        orig_name = "Current Account"
        AccountTestFactory(name=orig_name)

        # Which he sees when he opens the app
        accounts = self.get_json(URLS.account)
        acc_data = next(x for x in accounts if x['name'] == orig_name)

        # It now decides to change the name
        new_name = "Current Account (La Caixa)"
        self.patch_json(f"{URLS.account}{acc_data['pk']}/", {"name": new_name})

        # And he sees it worked, and he is happy
        accounts = self.get_json(URLS.account)
        _assert_contains(accounts, 'name', new_name)
        _assert_not_contains(accounts, 'name', orig_name)

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
            f"{URLS.account}{cur_acc.pk}/",
            {"name": "Current Account Itau"}
        )
        # And sees that it worked
        accounts = self.get_json(URLS.account)
        _assert_contains(accounts, 'name', 'Current Account Itau')
        _assert_not_contains(accounts, 'name', "Current Account")

        # He creates the new father for it
        new_father_data = {
            "name": "Current Account",
            "parent": root.pk,
            "acc_type": "Branch"
        }
        new_father = self.post_json(URLS.account, new_father_data)
        # And sees that it worked
        accounts = self.get_json(URLS.account)
        _assert_contains(accounts, 'name', new_father_data['name'])

        # He sets the old acc to have this father
        resp_data = self.patch_json(
            f"{URLS.account}{cur_acc.pk}/",
            json={"parent": new_father['pk']}
        )
        assert resp_data['parent'] == new_father['pk']

        # And creates the new account
        self.post_json(
            URLS.account,
            json={
                "name": "Current Account LaCaixa",
                "parent": new_father['pk'],
                "acc_type": "Leaf"
            }
        )

        accounts = self.get_json(URLS.account)
        _assert_contains(accounts, 'name', "Current Account LaCaixa")

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
            self.post_json(URLS.account, raw_data) for raw_data in accs_raw_data
        ]

        # And the Yen currency
        euro_raw_data = {"name": "Yen"}
        euro = self.post_json(URLS.currency, euro_raw_data)

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
        self.post_json(URLS.transaction, trans_raw_data)

        # Which now appears when querying for all transactions
        get_trans_resp = self.get_json(URLS.transaction)
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
        assert self.get_json(f"{URLS.transaction}?account_id={accs[0].pk}") == \
            serialized_transactions

        # He adds a new transaction of 10 cur to acc2
        new_transaction = self.post_json(
            URLS.transaction,
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
        assert self.get_json(f"{URLS.transaction}?account_id={accs[0].pk}") == \
            serialized_transactions

    def test_get_account_journal(self):
        # The user creates two accounts
        root_acc = _find_root(self.get_json(URLS.account))
        cash_account_data = {
            "name": "Cash",
            "acc_type": "Leaf",
            "parent": root_acc['pk']
        }
        cash_account = self.post_json(URLS.account, cash_account_data)
        bank_account_data = {
            "name": "Bank",
            "acc_type": "Leaf",
            "parent": root_acc['pk']
        }
        bank_account = self.post_json(URLS.account, bank_account_data)

        # And two transactions
        euro = _select_by(self.get_json(URLS.currency), 'name', 'Euro')
        withdrawal_data = {
            "description": "withdrawal",
            "date": "2018-01-01",
            "movements_specs": [
                {
                    "account": bank_account['pk'],
                    "money": {
                        "quantity": -100,
                        "currency": euro['pk']
                    }
                },
                {
                    "account": cash_account['pk'],
                    "money": {
                        "quantity": 100,
                        "currency": euro['pk']
                    }
                }
            ]
        }
        withdrawal = self.post_json(URLS.transaction, withdrawal_data)
        deposit_data = {
            "description": "deposit",
            "date": "2018-01-02",
            "movements_specs": [
                {
                    "account": cash_account['pk'],
                    "money": {
                        "quantity": -25,
                        "currency": euro['pk']
                    }
                },
                {
                    "account": bank_account['pk'],
                    "money": {
                        "quantity": 25,
                        "currency": euro['pk']
                    }
                }
            ]
        }
        deposit = self.post_json(URLS.transaction, deposit_data)

        # It queries for the journal of the bank account
        journal = self.get_json(f'{URLS.account}{bank_account["pk"]}/journal/')

        # It sees the account pk and both transactions there
        assert journal['account'] == bank_account['pk']
        assert len(journal['transactions']) == 2

        # And the balances after each transaction
        assert journal['balances'][0] == [
            {"currency": euro['pk'], "quantity": "-100.00000"}
        ]
        assert journal['balances'][1] == [
            {"currency": euro['pk'], "quantity": "-75.00000"}
        ]

        # And the transactions
        assert journal['transactions'][0] == withdrawal
        assert journal['transactions'][1] == deposit


#
# Helpers
#
class URLS:
    account = '/accounts/'
    currency = '/currencies/'
    transaction = '/transactions/'


def _find_root(acc_list):
    """ Returns the root account out of a list of accounts """
    return next(a for a in acc_list if a['acc_type'] == 'Root')


def _assert_contains(list_, key, value):
    """ Asserts that one of the dictionaries in list_ has a key whose
    value is equal to name """
    assert any(x[key] == value for x in list_), \
        f"{value} not found for key {key} in list {list_}"


def _assert_not_contains(list_, key, value):
    """ Opposite of _assert_contains """
    assert not any(x[key] == value for x in list_), \
        f"{value} WAS FOUND for key {key} in list {list_}"


def _select_by(list_, key, value):
    """ Selects the (first) dict from list_ that has value in it's key """
    return next(x for x in list_ if x[key] == value)


@attr.s()
class _TestRequests():
    """ A wrapper around `requests` to make requests for the
    testing server """

    # The base url
    url = attr.ib()

    # Default headers sent in every request
    headers = attr.ib()

    def get(self, path):
        return requests.get(f"{self.url}{path}", headers=self.headers)

    def post(self, path, json={}):
        return requests.post(
            f"{self.url}{path}",
            json=json,
            headers=self.headers
        )

    def patch(self, path, json={}):
        return requests.patch(
            f"{self.url}{path}",
            json=json,
            headers=self.headers
        )

    def delete(self, path):
        return requests.delete(f"{self.url}{path}", headers=self.headers)

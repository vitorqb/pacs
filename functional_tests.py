from datetime import date
from functools import partialmethod

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


class URLS:
    account = '/accounts/'
    currency = '/currencies/'
    transaction = '/transactions/'
    reports = '/reports/'


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

        # Sets up a root account and the DataMaker
        self.root_acc = _find_root(self.get_json(URLS.account))
        self.data_maker = DataMaker(self.root_acc)

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

    get_currencies = partialmethod(get_json, URLS.currency)

    def post_json(self, path, json={}):
        """ Makes a json request, ensures it returns 2**, and parses the json """
        resp = self.requests.post(f"{path}", json=json)
        self.assert_response_status_okay(resp)
        return resp.json()

    post_account = partialmethod(post_json, URLS.account)
    post_transaction = partialmethod(post_json, URLS.transaction)
    post_currency = partialmethod(post_json, URLS.currency)

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
        expenses = self.post_account(self.data_maker.expenses_acc())
        supermarket = self.post_account(self.data_maker.supermarket_acc(expenses))

        assert supermarket['parent'] == expenses['pk']
        assert supermarket['acc_type'] == "Leaf"
        assert supermarket['name'] == "Supermarket"

        # And he can see them
        accounts = self.get_json(URLS.account)
        for x in 'Expenses', 'Supermarket':
            _assert_contains(accounts, 'name', x)

    def test_user_changes_name_of_account(self):
        # The user had previously creates an account
        assets = self.post_account(self.data_maker.assets_acc())
        current_acc = self.post_account(self.data_maker.current_acc(assets))
        orig_name = current_acc['name']

        # Which he sees when he opens the app
        acc_data = _select_by(self.get_json(URLS.account), 'name', orig_name)

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
        assets = self.post_account(self.data_maker.assets_acc())
        cur_acc = self.post_account(self.data_maker.current_acc(assets))

        # Now it wants to have Current Accounts as a child of Root, and
        # two specific accounts for two different Current Accounts
        # .
        # | -- Assets
        # |    |-- Current Account
        # |    |   |-- Current Account Itau
        # |    |   `-- Current Account LaCaixa

        # It currects the name of the existant account
        self.patch_json(
            f"{URLS.account}{cur_acc['pk']}/",
            {"name": "Current Account Itau"}
        )
        # And sees that it worked
        accounts = self.get_json(URLS.account)
        _assert_contains(accounts, 'name', 'Current Account Itau')
        _assert_not_contains(accounts, 'name', cur_acc['name'])

        # He creates the new father for it
        new_father = self.post_account({
            "name": "Current Account",
            "parent": assets['pk'],
            "acc_type": "Branch"
        })
        # And sees that it worked
        accounts = self.get_json(URLS.account)
        _assert_contains(accounts, 'name', new_father['name'])

        # He sets the old acc to have this father
        resp_data = self.patch_json(
            f"{URLS.account}{cur_acc['pk']}/",
            json={"parent": new_father['pk']}
        )
        assert resp_data['parent'] == new_father['pk']

        # And creates the new account
        self.post_account({
                "name": "Current Account LaCaixa",
                "parent": new_father['pk'],
                "acc_type": "Leaf"
        })
        accounts = self.get_json(URLS.account)
        _assert_contains(accounts, 'name', "Current Account LaCaixa")

    def test_first_transaction(self):
        # The user creates two accounts
        assets = self.post_account(self.data_maker.assets_acc())
        salary = self.post_account(self.data_maker.salary_acc(assets))
        money = self.post_account(self.data_maker.money_acc(assets))

        # And the Yen currency
        euro = self.post_currency({"name": "Yen"})

        # And it's first transaction ever!
        trans_raw_data = self.data_maker.earn_money_tra(salary, money, euro)
        self.post_transaction(trans_raw_data)

        # Which now appears when querying for all transactions
        transactions = self.get_json(URLS.transaction)
        assert len(transactions) == 1
        assert transactions[0]['date'] == trans_raw_data['date']
        assert transactions[0]['description'] == trans_raw_data['description']

    def test_check_balance_and_add_transaction(self):
        # The user has two accounts he uses, with two transactions between them,
        # namely a deposit and a withdrawal
        cur = self.post_currency({"name": "Yen"})
        assets = self.post_account(self.data_maker.assets_acc())
        current_acc = self.post_account(self.data_maker.current_acc(assets))
        money_acc = self.post_account(self.data_maker.money_acc(assets))
        deposit = self.post_transaction(
            self.data_maker.deposit(current_acc, money_acc, cur)
        )
        withdrawal = self.post_transaction(
            self.data_maker.withdrawal(current_acc, money_acc, cur)
        )
        transactions = [deposit, withdrawal]
        transactions.sort(key=lambda x: x['date'], reverse=True)

        # He also paid a supermarket with money
        expenses = self.post_account(self.data_maker.expenses_acc())
        supermarket = self.post_account(self.data_maker.supermarket_acc(expenses))
        paid_supermarket = self.post_transaction(
            self.data_maker.paid_supermarket(money_acc, supermarket, cur)
        )

        # He queries ony for transactions involving current_acc, and see the
        # same ones listed, in chronological order
        current_acc_transactions = (
            self.get_json(f"{URLS.transaction}?account_id={current_acc['pk']}")
        )
        assert current_acc_transactions == transactions

        # He adds a new withdrawal of 10 cur to money
        new_withdrawal = self.post_transaction(self.data_maker.withdrawal(
            current_acc,
            money_acc,
            cur,
            date_='2018-01-03'
        ))
        transactions.insert(0, new_withdrawal)
        transactions.sort(key=lambda x: x['date'], reverse=True)

        # He queries again for transactions involving acc1, and see all
        # of them listed
        current_acc_transactions = (
            self.get_json(f"{URLS.transaction}?account_id={current_acc['pk']}")
        )
        assert current_acc_transactions == transactions

    def test_get_account_journal(self):
        # The user creates two accounts
        assets = self.post_account(self.data_maker.assets_acc())
        cash_account = self.post_account(self.data_maker.money_acc(assets))
        bank_account = self.post_account(self.data_maker.current_acc(assets))

        # And two transactions
        euro = _select_by(self.get_json(URLS.currency), 'name', 'Euro')
        withdrawal = self.post_transaction(self.data_maker.withdrawal(
            bank_account, cash_account, euro, date_='2018-01-03'
        ))
        deposit = self.post_transaction(self.data_maker.deposit(
            bank_account, cash_account, euro, date_='2018-01-02'
        ))

        # It queries for the journal of the bank account
        journal = self.get_json(f'{URLS.account}{bank_account["pk"]}/journal/')

        # It sees the account pk
        assert journal['account'] == bank_account['pk']

        # And the balances after each transaction.
        assert journal['balances'] == [
            [{"currency": euro['pk'], "quantity": "1000.00000"}],
            [{"currency": euro['pk'], "quantity": "880.00000"}]
        ]

        # And the transactions
        transactions = sorted([withdrawal, deposit], key=lambda x: x['date'])
        assert journal['transactions'] == transactions

        # He then queries for the journal for Cash, in reverse order (last first)
        journal = self.get_json(
            f'{URLS.account}{cash_account["pk"]}/journal/?reverse=1'
        )
        assert journal['account'] == cash_account['pk']
        assert journal['balances'] == [
            [{"currency": euro['pk'], "quantity": "-880.00000"}],
            [{"currency": euro['pk'], "quantity": "-1000.00000"}]
        ]
        assert journal['transactions'] == transactions[::-1]

    def test_get_accounts_evolution_report(self):
        euro = _select_by(self.get_currencies(), 'name', 'Euro')

        # The user has three (leaf) accounts: bank, cash, supermarket
        assets = self.post_account(self.data_maker.assets_acc())
        expenses = self.post_account(self.data_maker.expenses_acc())
        bank = self.post_account(self.data_maker.current_acc(assets))
        cash = self.post_account(self.data_maker.money_acc(assets))
        supermarket = self.post_account(self.data_maker.supermarket_acc(expenses))

        # And some transactions
        self.post_transaction(
            self.data_maker.deposit(bank, cash, euro, "2016-01-01")
        )
        self.post_transaction(
            self.data_maker.paid_supermarket(bank, supermarket, euro, "2017-02-28")
        )
        self.post_transaction(
            self.data_maker.withdrawal(bank, cash, euro, "2017-02-28")
        )

        # It queries for the balance evolution report
        balance_evol_report_req = {
            "periods": [
                ["2016-12-01", "2016-12-31"],
                ["2017-01-01", "2017-01-31"],
                ["2017-02-01", "2017-02-28"]
            ],
            "accounts": [bank['pk'], cash['pk'], supermarket['pk']]
        }
        balance_evol_report = self.post_json(
            f"{URLS.reports}balance-evolution/",
            balance_evol_report_req
        )

        # The returned data contains the same periods
        assert balance_evol_report['periods'] == balance_evol_report_req['periods']

        # And the three accounts
        accounts_in_report = [
            x['account'] for x in balance_evol_report['data']
        ]
        assert accounts_in_report == balance_evol_report_req['accounts']

        # The initial balance for the supermarket should be 0
        supermarket_report_data = _select_by(
            balance_evol_report['data'], 'account', supermarket['pk']
        )
        assert supermarket_report_data['initial_balance'] == []

        # And for the others should be the balance from the deposit
        bank_report_data = _select_by(
            balance_evol_report['data'], 'account', bank['pk']
        )
        assert bank_report_data['initial_balance'] == [
            {"currency": euro['pk'], "quantity": "1000.00000"}
        ]
        cash_report_data = _select_by(
            balance_evol_report['data'], 'account', cash['pk']
        )
        assert cash_report_data['initial_balance'] == [
            {"currency": euro['pk'], "quantity": "-1000.00000"}
        ]

        # Now focusing on bank, we expect three balance evolutions, one for each
        # period
        assert len(bank_report_data['balance_evolution']) == 3

        # The first two should be zero (no transactions in this period)
        assert bank_report_data['balance_evolution'][0:2] == [[], []]

        # And the thrid should have both withdrawal and paid_supermarket
        assert bank_report_data['balance_evolution'][2] == [
            {"currency": euro['pk'], "quantity": '-240.00000'}
        ]


#
# Helpers
#
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


@attr.s()
class DataMaker:
    """ Helper to make json data for the requests """

    # The root account
    root_acc = attr.ib()

    def expenses_acc(self):
        return {
            "name": "Expenses",
            "acc_type": "Branch",
            "parent": self.root_acc['pk']
        }

    def supermarket_acc(self, parent):
        return {
            "name": "Supermarket",
            "acc_type": "Leaf",
            "parent": parent['pk']
        }

    def current_acc(self, parent):
        return {
            "name": "Current Account",
            "acc_type": "Leaf",
            "parent": parent["pk"]
        }

    def assets_acc(self):
        return {
            "name": "Assets",
            "acc_type": "Branch",
            "parent": self.root_acc["pk"]
        }

    def salary_acc(self, parent):
        return {
            "name": "Salary",
            "acc_type": "Leaf",
            "parent": parent["pk"]
        }

    def money_acc(self, parent):
        return {
            "name": "Money",
            "acc_type": "Leaf",
            "parent": parent['pk']
        }

    def earn_money_tra(self, from_acc, to_acc, curr):
        return {
            "description": "Earned some money!",
            "date": "2018-01-01",
            "movements_specs": [
                {
                    "account": from_acc['pk'],
                    "money": {
                        "quantity": -1000,
                        "currency": curr['pk']
                    }
                },
                {
                    "account": to_acc['pk'],
                    "money": {
                        "quantity": 1000,
                        "currency": curr['pk']
                    }
                },
            ]
        }

    def deposit(self, accbank, accmoney, curr, date_=None):
        return {
            "description": "Deposit",
            "date": date_ or "2018-02-11",
            "movements_specs": [
                {
                    "account": accmoney['pk'],
                    "money": {
                        "quantity": -1000,
                        "currency": curr['pk']
                    }
                },
                {
                    "account": accbank['pk'],
                    "money": {
                        "quantity": 1000,
                        "currency": curr['pk']
                    }
                },
            ]
        }

    def withdrawal(self, accbank, accmoney, curr, date_=None):
        return {
            "description": "Withdrawal",
            "date": date_ or "2018-03-11",
            "movements_specs": [
                {
                    "account": accbank['pk'],
                    "money": {
                        "quantity": "-120",
                        "currency": curr['pk']
                    }
                },
                {
                    "account": accmoney['pk'],
                    "money": {
                        "quantity": "120",
                        "currency": curr['pk']
                    }
                },
            ]
        }

    def paid_supermarket(self, accfrom, accto, curr, date_=None):
        return {
            "description": "Supermarket!",
            "date": date_ or "2017-12-21",
            "movements_specs": [
                {
                    "account": accfrom['pk'],
                    "money": {
                        "quantity": "-120",
                        "currency": curr['pk']
                    }
                },
                {
                    "account": accto['pk'],
                    "money": {
                        "quantity": "120",
                        "currency": curr['pk']
                    }
                },
            ]
        }

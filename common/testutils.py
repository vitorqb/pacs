from decimal import Decimal
from functools import partialmethod

import attr
import requests
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

import common.models
import exchangerates.models
from accounts.management.commands.populate_accounts import (
    account_populator,
    account_type_populator,
)
from currencies.management.commands.populate_currencies import currency_populator


class URLS:
    account = "/accounts/"
    currency = "/currencies/"
    transaction = "/transactions/"

    class reports:
        _base = "/reports/"
        flow_evolution = _base + "flow-evolution/"
        balance_evolution = _base + "balance-evolution/"

    class exchange_rates:
        _base = "/exchange_rates/"
        data = _base + "data/v2"


class PacsTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient(HTTP_AUTHORIZATION="TOKEN valid_token")

    @staticmethod
    def populate_accounts():
        """Populates db with Accounts"""
        account_type_populator()
        account_populator()

    @staticmethod
    def populate_currencies():
        currency_populator()

    def tearDown(self):
        """Clear cache between tests"""
        super().tearDown()
        cache.clear()


@attr.s()
class MockQset:
    """A mock for a queryset that records the arguments its methods were called
    ald returns itself instead of a copy"""

    # Used internally for setting an iterator
    _iter_list = attr.ib(init=False, default=None)

    # Was this queryset called with .none() ?
    is_none = attr.ib(default=False)

    filter_kwargs = attr.ib(init=False, default=None)
    prefetch_related_args = attr.ib(init=False, default=None)
    order_by_args = attr.ib(init=False, default=None)
    filter_by_account_args = attr.ib(init=False, default=False)
    distinct_called = attr.ib(init=False, default=False)

    def filter(self, **kwargs):
        self.filter_kwargs = kwargs
        return self

    def prefetch_related(self, *args):
        self.prefetch_related_args = args
        return self

    def order_by(self, *args):
        self.order_by_args = args
        return self

    def distinct(self):
        self.distinct_called = True
        return self

    def filter_by_account(self, *args):
        self.filter_by_account_args = args
        return self

    def none(self):
        """Returns a new queryset with is_none=True"""
        return MockQset(is_none=True)

    def set_iter(self, x):
        """Sets a list to be used when called as an iterator."""
        self._iter_list = x

    def __iter__(self):
        """Iterates through self._iter_list, that must have been set by
        self.set_iter before."""
        assert self._iter_list is not None
        return iter(self._iter_list)


@attr.s()
class TestRequests:
    """A wrapper around `requests` to make requests for the
    testing server"""

    __test__ = False

    # The base url
    url = attr.ib()

    # Default headers sent in every request
    headers = attr.ib(default={"authorization": "TOKEN valid_token"})

    def get(self, path, params=None, extra_headers={}):
        params = params or {}
        headers = {**self.headers, **extra_headers}
        return requests.get(f"{self.url}{path}", params=params, headers=headers)

    def post(self, path, json=None, files=None, params=None):
        json = json or {}
        files = files or {}
        params = params or {}
        return requests.post(
            f"{self.url}{path}", json=json, files=files, params=params, headers=self.headers
        )

    def patch(self, path, json=None):
        json = json or {}
        return requests.patch(f"{self.url}{path}", json=json, headers=self.headers)

    def delete(self, path):
        return requests.delete(f"{self.url}{path}", headers=self.headers)


def populate_exchangerates_with_mock_data():
    for x in (
        {"currency_code": "EUR", "date": "2020-01-01", "value": Decimal("1")},
        {"currency_code": "BRL", "date": "2020-01-01", "value": Decimal("0.25")},
        {"currency_code": "BRL", "date": "2020-01-06", "value": Decimal("0.2")},
    ):
        common.models.full_clean_and_save(exchangerates.models.ExchangeRate(**x))


@attr.s()
class DataMaker:
    """Helper to make json data for the requests"""

    # The root account
    root_acc = attr.ib()

    def expenses_acc(self):
        return {"name": "Expenses", "acc_type": "Branch", "parent": self.root_acc["pk"]}

    def revenues_acc(self):
        return {
            "name": "Revenue",
            "acc_type": "Branch",
            "parent": self.root_acc["pk"],
        }

    def supermarket_acc(self, parent):
        return {"name": "Supermarket", "acc_type": "Leaf", "parent": parent["pk"]}

    def current_acc(self, parent):
        return {"name": "Current Account", "acc_type": "Leaf", "parent": parent["pk"]}

    def assets_acc(self):
        return {"name": "Assets", "acc_type": "Branch", "parent": self.root_acc["pk"]}

    def salary_acc(self, parent):
        return {"name": "Salary", "acc_type": "Leaf", "parent": parent["pk"]}

    def money_acc(self, parent):
        return {"name": "Money", "acc_type": "Leaf", "parent": parent["pk"]}

    def salary_tra(self, date, from_acc, to_acc, quantity, curr):
        return {
            "description": "Salary",
            "date": date,
            "movements_specs": [
                {
                    "account": from_acc["pk"],
                    "money": {
                        "quantity": -quantity,
                        "currency": curr["pk"],
                    },
                },
                {
                    "account": to_acc["pk"],
                    "money": {
                        "quantity": quantity,
                        "currency": curr["pk"],
                    },
                },
            ],
        }

    def earn_money_tra(self, from_acc, to_acc, curr):
        return {
            "description": "Earned some money!",
            "date": "2018-01-01",
            "tags": [
                {
                    "name": "earning-type",
                    "value": "ocasional",
                }
            ],
            "movements_specs": [
                {"account": from_acc["pk"], "money": {"quantity": -1000, "currency": curr["pk"]}},
                {"account": to_acc["pk"], "money": {"quantity": 1000, "currency": curr["pk"]}},
            ],
        }

    def deposit(self, accbank, accmoney, curr, date_=None):
        return {
            "description": "Deposit",
            "date": date_ or "2018-02-11",
            "movements_specs": [
                {"account": accmoney["pk"], "money": {"quantity": -1000, "currency": curr["pk"]}},
                {"account": accbank["pk"], "money": {"quantity": 1000, "currency": curr["pk"]}},
            ],
        }

    def withdrawal(self, accbank, accmoney, curr, date_=None):
        return {
            "description": "Withdrawal",
            "date": date_ or "2018-03-11",
            "movements_specs": [
                {"account": accbank["pk"], "money": {"quantity": "-120", "currency": curr["pk"]}},
                {"account": accmoney["pk"], "money": {"quantity": "120", "currency": curr["pk"]}},
            ],
        }

    def paid_supermarket(self, accfrom, accto, curr, date_=None, reference=None):
        out = {
            "description": "Supermarket!",
            "date": date_ or "2017-12-21",
            "movements_specs": [
                {"account": accfrom["pk"], "money": {"quantity": "-120", "currency": curr["pk"]}},
                {"account": accto["pk"], "money": {"quantity": "120", "currency": curr["pk"]}},
            ],
        }
        if reference:
            out["reference"] = reference
        return out


@attr.s()
class TestRequestMaker:

    __test__ = False

    test_requests: TestRequests = attr.ib()

    @staticmethod
    def assert_response_status_okay(resp):
        """Asserts that a Response has a 2xx status code"""
        assert str(resp.status_code)[0] == "2", (
            f"Response for {resp.url} had status code "
            + f"{resp.status_code} and not 2xx. \nContent: {resp.content}"
        )

    def get_json(self, path, params=None):
        """
        Makes a get request, ensures that it returns 2**, and parses the json
        """
        resp = self.test_requests.get(f"{path}", params=params)
        self.assert_response_status_okay(resp)
        return resp.json()

    def post_json(self, path, json={}):
        """Makes a json request, ensures it returns 2**, and parses the json"""
        resp = self.test_requests.post(f"{path}", json=json)
        self.assert_response_status_okay(resp)
        return resp.json()

    def patch_json(self, path, json={}):
        """Makes a json request, ensures it returns 2**, and parses the json"""
        resp = self.test_requests.patch(f"{path}", json=json)
        self.assert_response_status_okay(resp)
        return resp.json()

    def delete_pk(self, path, pk):
        """Makes a DELETE request, ensures it returns 2**, and parses the json"""
        resp = self.test_requests.delete(f"{path}{pk}/")
        self.assert_response_status_okay(resp)
        return resp

    get_accounts = partialmethod(get_json, URLS.account)
    get_currencies = partialmethod(get_json, URLS.currency)
    get_transactions = partialmethod(get_json, URLS.transaction)
    get_exchange_rates_data = partialmethod(get_json, URLS.exchange_rates.data)
    post_account = partialmethod(post_json, URLS.account)
    post_transaction = partialmethod(post_json, URLS.transaction)
    post_currency = partialmethod(post_json, URLS.currency)
    post_flow_evolution_report = partialmethod(post_json, URLS.reports.flow_evolution)
    post_balance_evolution_report = partialmethod(post_json, URLS.reports.balance_evolution)
    delete_transaction = partialmethod(delete_pk, URLS.transaction)


class TestHelpers:
    @staticmethod
    def find_root(acc_list):
        """Returns the root account out of a list of accounts"""
        return next(a for a in acc_list if a["acc_type"] == "Root")

    @staticmethod
    def assert_contains(list_, key, value):
        """Asserts that one of the dictionaries in list_ has a key whose
        value is equal to name"""
        assert any(
            x[key] == value for x in list_
        ), f"{value} not found for key {key} in list {list_}"

    @staticmethod
    def assert_not_contains(list_, key, value):
        """Opposite of assert_contains"""
        assert not any(
            x[key] == value for x in list_
        ), f"{value} WAS FOUND for key {key} in list {list_}"

    @staticmethod
    def select_by(list_, key, value):
        """Selects the (first) dict from list_ that has value in it's key"""
        return next(x for x in list_ if x[key] == value)

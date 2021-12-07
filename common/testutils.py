import attr
import requests
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from accounts.management.commands.populate_accounts import (account_populator,
                                                            account_type_populator)
from currencies.management.commands.populate_currencies import \
    currency_populator
import common.models
import exchangerates.models
from decimal import Decimal


class PacsTestCase(APITestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient(HTTP_AUTHORIZATION="TOKEN valid_token")

    @staticmethod
    def populate_accounts():
        """ Populates db with Accounts """
        account_type_populator()
        account_populator()

    @staticmethod
    def populate_currencies():
        currency_populator()

    def tearDown(self):
        """ Clear cache between tests """
        super().tearDown()
        cache.clear()


@attr.s()
class MockQset():
    """ A mock for a queryset that records the arguments its methods were called
    ald returns itself instead of a copy """

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
        """ Returns a new queryset with is_none=True """
        return MockQset(is_none=True)

    def set_iter(self, x):
        """ Sets a list to be used when called as an iterator. """
        self._iter_list = x

    def __iter__(self):
        """ Iterates through self._iter_list, that must have been set by
        self.set_iter before. """
        assert self._iter_list is not None
        return iter(self._iter_list)


@attr.s()
class TestRequests():
    """ A wrapper around `requests` to make requests for the
    testing server """

    __test__ = False

    # The base url
    url = attr.ib()

    # Default headers sent in every request
    headers = attr.ib(default={'authorization': "TOKEN valid_token"})

    def get(self, path, params=None, extra_headers={}):
        params = params or {}
        headers = {**self.headers, **extra_headers}
        return requests.get(f"{self.url}{path}", params=params, headers=headers)

    def post(self, path, json=None, files=None, params=None):
        json = json or {}
        files = files or {}
        params = params or {}
        return requests.post(
            f"{self.url}{path}",
            json=json,
            files=files,
            params=params,
            headers=self.headers
        )

    def patch(self, path, json=None):
        json = json or {}
        return requests.patch(
            f"{self.url}{path}",
            json=json,
            headers=self.headers
        )

    def delete(self, path):
        return requests.delete(f"{self.url}{path}", headers=self.headers)


def populate_exchangerates_with_mock_data():
    for x in (
            {"currency_code": "EUR", "date": "2020-01-01", "value": Decimal('1')},
            {"currency_code": "BRL", "date": "2020-01-01", "value": Decimal('0.25')},
            {"currency_code": "BRL", "date": "2020-01-06", "value": Decimal('0.2')}
    ):
        common.models.full_clean_and_save(exchangerates.models.ExchangeRate(**x))

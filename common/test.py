import attr
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from accounts.management.commands.populate_accounts import (account_populator,
                                                            account_type_populator)
from currencies.management.commands.populate_currencies import \
    currency_populator


class PacsTestCase(APITestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient(
            HTTP_AUTHORIZATION=f"Token {settings.ADMIN_TOKEN}"
        )

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

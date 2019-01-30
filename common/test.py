from django.conf import settings
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

    def populate_accounts(self):
        """ Populates db with Accounts """
        account_type_populator()
        account_populator()

    def populate_currencies(self):
        currency_populator()

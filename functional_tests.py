from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from accounts.management.commands.populate_accounts import (
    account_type_populator,
    account_populator,
    ACCOUNT_DATA
)
from currencies.management.commands.populate_currencies import (
    currency_populator,
    CURRENCIES_DATA
)
import requests


class FunctionalTests(StaticLiveServerTestCase):

    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()
        currency_populator()

    def get_json(self, url):
        """ Makes a request, ensures that it returns 2**, and parses the json """
        resp = requests.get(f"{self.live_server_url}/accounts/")
        assert str(resp.status_code)[0] == "2", \
            f"Response had status code {resp.status_code} and not 2xx"
        return resp.json()

    def test_creates_an_account_hierarchy(self):
        # The user enters and only sees the default accounts there
        resp_accs = self.get_json('/accounts/')
        assert len(resp_accs) == len(ACCOUNT_DATA)
        resp_accs_names = set(x['name'] for x in resp_accs)
        exp_accs_names = set(x['name'] for x in ACCOUNT_DATA)
        assert resp_accs_names == exp_accs_names

        # The user decides to add Expenses and Supermarket
        root_acc_pk = next(x['pk'] for x in resp_accs if x['acc_type'] == 'Root')
        expenses_acc = {
            "name": "Expenses",
            "acc_type": "Branch",
            "parent": root_acc_pk
        }
        expenses_resp = requests.post(
            f"{self.live_server_url}/accounts/",
            json=expenses_acc
        )
        assert expenses_resp.status_code == 201

        expenses_resp_pk = expenses_resp.json()['pk']
        supermarket_acc = {
            "name": "Supermarket",
            "acc_type": "Leaf",
            "parent": expenses_resp_pk
        }
        supermarket_resp = requests.post(
            f"{self.live_server_url}/accounts/",
            json=supermarket_acc
        )
        assert supermarket_resp.status_code == 201

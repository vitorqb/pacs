import requests

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
            f"Response for {url} had status code {resp.status_code} and not 2xx"
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

    def test_user_changes_name_of_account(self):
        # The user had previously creates an account
        orig_name = "Current Account"
        AccountTestFactory(name=orig_name)

        # Which he sees when he opens the app
        resp = requests.get(f"{self.live_server_url}/accounts/")
        assert orig_name in [x['name'] for x in resp.json()]
        acc_data = next(x for x in resp.json() if x['name'] == orig_name)

        # It now decides to change the name
        new_name = "Current Account (La Caixa)"
        resp = requests.patch(
            f"{self.live_server_url}/accounts/{acc_data['pk']}/",
            json={"name": new_name}
        )
        assert resp.status_code == 200, resp.content

        # And he sees it worked, and he is happy
        # !!!! SEMLL -> Repeated
        resp = requests.get(f"{self.live_server_url}/accounts/")
        assert new_name in [x['name'] for x in resp.json()]

    def test_user_changes_account_hierarchy(self):
        # The user had previously created an Current Account whose
        # father was Root Account
        root = get_root_acc()
        cur_acc = AccountTestFactory(
            name="Current Account",
            parent=root,
            acc_type=AccountType.objects.get(name="Leaf")
        )

        # Now it wants to have Current Accounts as a child of Root, and
        # two specific accounts for two different Current Accounts
        # .
        # | -- Root Account
        # |    |-- Current Account
        # |    |   |-- Current Account Itau
        # |    |   `-- Current Account LaCaixa

        # It currects the name of the existant account
        resp = requests.patch(
            f"{self.live_server_url}/accounts/{cur_acc.pk}/",
            json={"name": "Current Account Itau"}
        )
        assert resp.status_code == 200, resp.content
        # And sees that it worked
        resp = requests.get(f"{self.live_server_url}/accounts/")
        assert "Current Account Itau" in [x['name'] for x in resp.json()]

        # He creates the new father for it
        new_cur_acc_data = {
            "name": "Current Account",
            "parent": root.pk,
            "acc_type": "Branch"
        }
        resp = requests.post(
            f"{self.live_server_url}/accounts/",
            json=new_cur_acc_data
        )
        assert resp.status_code == 201, resp.content
        # And sees that it worked
        resp = requests.get(f"{self.live_server_url}/accounts/")
        assert "Current Account" in [x['name'] for x in resp.json()]
        new_cur_acc_pk = next(
            x['pk'] for x in resp.json() if x['name'] == "Current Account"
        )

        # He sets the old acc to have this father
        resp = requests.patch(
            f"{self.live_server_url}/accounts/{cur_acc.pk}/",
            json={"parent": new_cur_acc_pk}
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()['parent'] == new_cur_acc_pk

        # And creates the new account
        resp = requests.post(
            f"{self.live_server_url}/accounts/",
            json={
                "name": "Current Account LaCaixa",
                "parent": new_cur_acc_pk,
                "acc_type": "Leaf"
            }
        )
        assert resp.status_code, 200

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

    def assert_response_status_okay(self, resp):
        """ Asserts that a Response has a 2xx status code """
        assert str(resp.status_code)[0] == "2", \
            f"Response for {url} had status code {resp.status_code} and not 2xx"

    def get_json(self, url):
        """ Makes a get request, ensures that it returns 2**, and parses the json """
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
        expenses_json = self.post_json("/accounts/", expenses_acc)

        expenses_pk = expenses_json['pk']
        supermarket_acc = {
            "name": "Supermarket",
            "acc_type": "Leaf",
            "parent": expenses_pk
        }
        self.post_json("/accounts/", supermarket_acc)

    def test_user_changes_name_of_account(self):
        # The user had previously creates an account
        orig_name = "Current Account"
        AccountTestFactory(name=orig_name)

        # Which he sees when he opens the app
        accs_json = self.get_json("/accounts/")
        assert orig_name in [x['name'] for x in accs_json]
        acc_data = next(x for x in accs_json if x['name'] == orig_name)

        # It now decides to change the name
        new_name = "Current Account (La Caixa)"
        self.patch_json(f"/accounts/{acc_data['pk']}/", {"name": new_name})

        # And he sees it worked, and he is happy
        self.assert_is_acc_name(new_name)

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
        self.patch_json(
            f"/accounts/{cur_acc.pk}/",
            {"name": "Current Account Itau"}
        )
        # And sees that it worked
        self.assert_is_acc_name("Current Account Itau")

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

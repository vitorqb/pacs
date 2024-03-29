from functools import partialmethod

import attr
import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from accounts.management.commands.populate_accounts import (
    ACCOUNT_DATA,
    account_populator,
    account_type_populator,
)
from common.testutils import (
    URLS,
    DataMaker,
    TestHelpers,
    TestRequestMaker,
    TestRequests,
    populate_exchangerates_with_mock_data,
)
from currencies.management.commands.populate_currencies import currency_populator


@pytest.mark.functional
class FunctionalTests(StaticLiveServerTestCase):
    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()
        currency_populator()

        # Sets up a request session with authorization header
        self.requests = TestRequests(self.live_server_url)

        # Sets up a root account and the DataMaker
        self.trm = TestRequestMaker(self.requests)
        self.root_acc = TestHelpers.find_root(self.trm.get_json(URLS.account))
        self.data_maker = DataMaker(self.root_acc)

    def test_unlogged_user_cant_make_queries(self):
        # The user tries to make a query without the header and sees 403
        self.requests.headers = {}
        assert (
            self.requests.get(URLS.account).status_code == 403
        ), "User should have been unauthorized because of no header!"

        # Then he puts the correct token and it works!
        self.requests.headers = {"authorization": "TOKEN valid_token"}
        assert (
            self.requests.get(URLS.account).status_code == 200
        ), "User should have been successfull becase he has the header with a valid token"

    def test_creates_an_account_hierarchy(self):
        # The user enters and only sees the default accounts there
        resp_accs = self.trm.get_accounts()
        assert len(resp_accs) == len(ACCOUNT_DATA)
        assert set(x["name"] for x in resp_accs) == set(x["name"] for x in ACCOUNT_DATA)

        # The user decides to add Expenses and Supermarket
        expenses = self.trm.post_account(self.data_maker.expenses_acc())
        supermarket = self.trm.post_account(self.data_maker.supermarket_acc(expenses))

        assert supermarket["parent"] == expenses["pk"]
        assert supermarket["acc_type"] == "Leaf"
        assert supermarket["name"] == "Supermarket"

        # And he can see them
        accounts = self.trm.get_accounts()
        for x in "Expenses", "Supermarket":
            TestHelpers.assert_contains(accounts, "name", x)

    def test_user_changes_name_of_account(self):
        # The user had previously creates an account
        assets = self.trm.post_account(self.data_maker.assets_acc())
        current_acc = self.trm.post_account(self.data_maker.current_acc(assets))
        orig_name = current_acc["name"]

        # Which he sees when he opens the app
        acc_data = TestHelpers.select_by(self.trm.get_accounts(), "name", orig_name)

        # It now decides to change the name
        new_name = "Current Account (La Caixa)"
        self.trm.patch_json(f"{URLS.account}{acc_data['pk']}/", {"name": new_name})

        # And he sees it worked, and he is happy
        accounts = self.trm.get_accounts()
        TestHelpers.assert_contains(accounts, "name", new_name)
        TestHelpers.assert_not_contains(accounts, "name", orig_name)

    def test_user_changes_account_hierarchy(self):
        # The user had previously created an Current Account whose
        # father was Root Account
        assets = self.trm.post_account(self.data_maker.assets_acc())
        cur_acc = self.trm.post_account(self.data_maker.current_acc(assets))

        # Now it wants to have Current Accounts as a child of Root, and
        # two specific accounts for two different Current Accounts
        # .
        # | -- Assets
        # |    |-- Current Account
        # |    |   |-- Current Account Itau
        # |    |   `-- Current Account LaCaixa

        # It currects the name of the existant account
        self.trm.patch_json(f"{URLS.account}{cur_acc['pk']}/", {"name": "Current Account Itau"})
        # And sees that it worked
        accounts = self.trm.get_accounts()
        TestHelpers.assert_contains(accounts, "name", "Current Account Itau")
        TestHelpers.assert_not_contains(accounts, "name", cur_acc["name"])

        # He creates the new father for it
        new_father = self.trm.post_account(
            {"name": "Current Account", "parent": assets["pk"], "acc_type": "Branch"}
        )
        # And sees that it worked
        accounts = self.trm.get_accounts()
        TestHelpers.assert_contains(accounts, "name", new_father["name"])

        # He sets the old acc to have this father
        resp_data = self.trm.patch_json(
            f"{URLS.account}{cur_acc['pk']}/", json={"parent": new_father["pk"]}
        )
        assert resp_data["parent"] == new_father["pk"]

        # And creates the new account
        self.trm.post_account(
            {"name": "Current Account LaCaixa", "parent": new_father["pk"], "acc_type": "Leaf"}
        )
        accounts = self.trm.get_accounts()
        TestHelpers.assert_contains(accounts, "name", "Current Account LaCaixa")

    def test_first_transaction(self):
        # The user creates two accounts
        assets = self.trm.post_account(self.data_maker.assets_acc())
        salary = self.trm.post_account(self.data_maker.salary_acc(assets))
        money = self.trm.post_account(self.data_maker.money_acc(assets))

        # And the Yen currency
        euro = self.trm.post_currency({"name": "Yen"})

        # And it's first transaction ever!
        trans_raw_data = self.data_maker.earn_money_tra(salary, money, euro)
        self.trm.post_transaction(trans_raw_data)

        # Which now appears when querying for all transactions
        transactions = self.trm.get_transactions()
        assert len(transactions) == 1
        assert transactions[0]["date"] == trans_raw_data["date"]
        assert transactions[0]["description"] == trans_raw_data["description"]
        assert transactions[0]["tags"] == trans_raw_data["tags"]
        # Reference is empty since we did not provide it.
        assert transactions[0]["reference"] is None

        # It adds a second one, with a reference
        expenses = self.trm.post_account(self.data_maker.expenses_acc())
        supermarket = self.trm.post_account(self.data_maker.supermarket_acc(expenses))
        reference = "MERCADONA-1212"
        supermarket_tra_data = self.data_maker.paid_supermarket(
            money, supermarket, euro, reference=reference
        )
        supermarket_tra = self.trm.post_transaction(supermarket_tra_data)

        # Which also appears when querying for all
        transactions = self.trm.get_transactions()
        assert len(transactions) == 2
        assert transactions[1]["pk"] == supermarket_tra["pk"]
        assert transactions[1]["reference"] == reference

        # Changes it's reference and sees that it works.
        url = f"{URLS.transaction}{supermarket_tra['pk']}/"
        self.trm.patch_json(url, json={"reference": None})
        patched_trans = self.trm.get_json(url)
        assert patched_trans["reference"] is None

    def test_check_balance_and_add_transaction(self):
        # The user has two accounts he uses, with two transactions between them,
        # namely a deposit and a withdrawal
        cur = self.trm.post_currency({"name": "Yen"})
        assets = self.trm.post_account(self.data_maker.assets_acc())
        current_acc = self.trm.post_account(self.data_maker.current_acc(assets))
        money_acc = self.trm.post_account(self.data_maker.money_acc(assets))
        deposit = self.trm.post_transaction(self.data_maker.deposit(current_acc, money_acc, cur))
        withdrawal = self.trm.post_transaction(
            self.data_maker.withdrawal(current_acc, money_acc, cur)
        )
        transactions = [deposit, withdrawal]
        transactions.sort(key=lambda x: x["date"], reverse=True)

        # He also paid a supermarket with money
        expenses = self.trm.post_account(self.data_maker.expenses_acc())
        supermarket = self.trm.post_account(self.data_maker.supermarket_acc(expenses))
        paid_supermarket = self.trm.post_transaction(
            self.data_maker.paid_supermarket(money_acc, supermarket, cur)
        )

        # He queries ony for transactions involving current_acc, and see the
        # same ones listed, in chronological order
        current_acc_transactions = self.trm.get_json(
            f"{URLS.transaction}?account_id={current_acc['pk']}"
        )
        assert current_acc_transactions == transactions

        # He adds a new withdrawal of 10 cur to money
        new_withdrawal = self.trm.post_transaction(
            self.data_maker.withdrawal(current_acc, money_acc, cur, date_="2018-01-03")
        )
        transactions.insert(0, new_withdrawal)
        transactions.sort(key=lambda x: x["date"], reverse=True)

        # He queries again for transactions involving acc1, and see all
        # of them listed
        current_acc_transactions = self.trm.get_json(
            f"{URLS.transaction}?account_id={current_acc['pk']}"
        )
        assert current_acc_transactions == transactions

    def test_get_account_journal(self):
        # The user creates two accounts
        assets = self.trm.post_account(self.data_maker.assets_acc())
        cash_account = self.trm.post_account(self.data_maker.money_acc(assets))
        bank_account = self.trm.post_account(self.data_maker.current_acc(assets))

        # And two transactions
        euro = TestHelpers.select_by(self.trm.get_currencies(), "name", "Euro")
        withdrawal = self.trm.post_transaction(
            self.data_maker.withdrawal(bank_account, cash_account, euro, date_="2018-01-03")
        )
        deposit = self.trm.post_transaction(
            self.data_maker.deposit(bank_account, cash_account, euro, date_="2018-01-02")
        )

        # It queries for the journal of the bank account
        journal = self.trm.get_json(f'{URLS.account}{bank_account["pk"]}/journal/')

        # It sees the account pk
        assert journal["account"] == bank_account["pk"]

        # And the balances after each transaction.
        assert journal["balances"] == [
            [{"currency": euro["pk"], "quantity": "1000.00000"}],
            [{"currency": euro["pk"], "quantity": "880.00000"}],
        ]

        # And the transactions
        transactions = sorted([withdrawal, deposit], key=lambda x: x["date"])
        assert journal["transactions"] == transactions

        # He then queries for the journal for Cash, in reverse order (last first)
        journal = self.trm.get_json(f'{URLS.account}{cash_account["pk"]}/journal/?reverse=1')
        assert journal["account"] == cash_account["pk"]
        assert journal["balances"] == [
            [{"currency": euro["pk"], "quantity": "-880.00000"}],
            [{"currency": euro["pk"], "quantity": "-1000.00000"}],
        ]
        assert journal["transactions"] == transactions[::-1]

    def test_get_accounts_evolution_report(self):
        euro = TestHelpers.select_by(self.trm.get_currencies(), "name", "Euro")

        # The user has three (leaf) accounts: bank, cash, supermarket
        assets = self.trm.post_account(self.data_maker.assets_acc())
        expenses = self.trm.post_account(self.data_maker.expenses_acc())
        bank = self.trm.post_account(self.data_maker.current_acc(assets))
        cash = self.trm.post_account(self.data_maker.money_acc(assets))
        supermarket = self.trm.post_account(self.data_maker.supermarket_acc(expenses))

        # And some transactions
        self.trm.post_transaction(self.data_maker.deposit(bank, cash, euro, "2016-01-01"))
        self.trm.post_transaction(
            self.data_maker.paid_supermarket(bank, supermarket, euro, "2017-02-28")
        )
        self.trm.post_transaction(self.data_maker.withdrawal(bank, cash, euro, "2017-02-28"))

        # It queries for the balance evolution report
        balance_evol_report_req = {
            "dates": ["2016-12-31", "2017-01-31", "2017-02-28"],
            "accounts": [bank["pk"], cash["pk"], supermarket["pk"]],
        }
        balance_evol_report = self.trm.post_balance_evolution_report(
            balance_evol_report_req,
        )["data"]

        # Three balances are returned
        assert len(balance_evol_report) == 9

        # The returned data contains the same dates
        dates_in_report = set(x["date"] for x in balance_evol_report)
        assert dates_in_report == set(balance_evol_report_req["dates"])

        # And the same accounts
        accounts_in_report = set(x["account"] for x in balance_evol_report)
        assert accounts_in_report == set(balance_evol_report_req["accounts"])

        # On the first and second dates, supermarket has no balance
        supermarket_0 = next(
            x
            for x in balance_evol_report
            if x["date"] == balance_evol_report_req["dates"][0]
            and x["account"] == supermarket["pk"]
        )
        supermarket_1 = next(
            x
            for x in balance_evol_report
            if x["date"] == balance_evol_report_req["dates"][1]
            and x["account"] == supermarket["pk"]
        )
        assert supermarket_0["balance"] == []
        assert supermarket_1["balance"] == []

        # Then we have the supermarket on the third one
        supermarket_2 = next(
            x
            for x in balance_evol_report
            if x["date"] == balance_evol_report_req["dates"][2]
            and x["account"] == supermarket["pk"]
        )
        assert supermarket_2["balance"] == [{"currency": euro["pk"], "quantity": "120.00000"}]

        # And for bank we start with a deposit of 1000
        bank_0 = next(
            x
            for x in balance_evol_report
            if x["date"] == balance_evol_report_req["dates"][0] and x["account"] == bank["pk"]
        )
        assert bank_0["balance"] == [{"currency": euro["pk"], "quantity": "1000.00000"}]

        # Same here, since no new transaction
        bank_1 = next(
            x
            for x in balance_evol_report
            if x["date"] == balance_evol_report_req["dates"][1] and x["account"] == bank["pk"]
        )
        assert bank_1["balance"] == [{"currency": euro["pk"], "quantity": "1000.00000"}]

        # Finally here a withdrawal and paid supermarket
        bank_2 = next(
            x
            for x in balance_evol_report
            if x["date"] == balance_evol_report_req["dates"][2] and x["account"] == bank["pk"]
        )
        assert bank_2["balance"] == [{"currency": euro["pk"], "quantity": "760.00000"}]

    def test_get_flow_report(self):
        # First select two currencies
        all_currencies = self.trm.get_currencies()
        euro = TestHelpers.select_by(all_currencies, "name", "Euro")
        real = TestHelpers.select_by(all_currencies, "name", "Real")

        # Create accounts for salary, current acc, and supermarket
        revenue_acc_data = self.data_maker.revenues_acc()
        revenue_acc = self.trm.post_account(revenue_acc_data)

        assets_acc_data = self.data_maker.assets_acc()
        assets_acc = self.trm.post_account(assets_acc_data)

        bank_acc_data = self.data_maker.current_acc(assets_acc)
        bank_acc = self.trm.post_account(bank_acc_data)

        expenses_acc_data = self.data_maker.expenses_acc()
        expenses_acc = self.trm.post_account(expenses_acc_data)

        salary_acc_data = self.data_maker.salary_acc(revenue_acc)
        salary_acc = self.trm.post_account(salary_acc_data)

        supermarket_acc_data = self.data_maker.supermarket_acc(expenses_acc)
        supermarket_acc = self.trm.post_account(supermarket_acc_data)

        # Receives three salaries, two in euro and one in real
        euro_salary_data = self.data_maker.salary_tra(
            date="2019-06-15",
            from_acc=salary_acc,
            to_acc=bank_acc,
            quantity=50,
            curr=euro,
        )
        euro_salary_one = self.trm.post_transaction(euro_salary_data)
        euro_salary_two = self.trm.post_transaction(euro_salary_data)

        real_salary_data = self.data_maker.salary_tra(
            date="2019-06-15",
            from_acc=salary_acc,
            to_acc=bank_acc,
            quantity=450,
            curr=real,
        )
        real_salary = self.trm.post_transaction(real_salary_data)

        # Two days later, goes to the supermarket
        supermarket_june_data = self.data_maker.paid_supermarket(
            accfrom=bank_acc,
            accto=supermarket_acc,
            curr=euro,
            date_="2019-06-17",
        )
        supermarket_june = self.trm.post_transaction(supermarket_june_data)

        # And then again in the following month
        supermarket_july_data = self.data_maker.paid_supermarket(
            accfrom=bank_acc,
            accto=supermarket_acc,
            curr=euro,
            date_="2019-07-01",
        )
        supermarket_july = self.trm.post_transaction(supermarket_july_data)

        # Asks for the report for june, july
        flow_report_opts = {
            "periods": [
                ["2019-06-01", "2019-06-30"],
                ["2019-07-01", "2019-07-31"],
            ],
            "accounts": [revenue_acc["pk"], expenses_acc["pk"]],
        }
        flow_report_data = self.trm.post_flow_evolution_report(flow_report_opts)

        # And for revenue we have the wages won and 0
        revenues_data = TestHelpers.select_by(
            flow_report_data["data"],
            "account",
            revenue_acc["pk"],
        )
        assert revenues_data["flows"] == [
            {
                "period": flow_report_opts["periods"][0],
                "moneys": [
                    {
                        "currency": euro["pk"],
                        "quantity": "-100.00000",
                    },
                    {
                        "currency": real["pk"],
                        "quantity": "-450.00000",
                    },
                ],
            },
            {"period": flow_report_opts["periods"][1], "moneys": []},
        ]

        # And for expenses...
        expenses_data = TestHelpers.select_by(
            flow_report_data["data"],
            "account",
            expenses_acc["pk"],
        )
        assert expenses_data["flows"] == [
            {
                "period": flow_report_opts["periods"][0],
                "moneys": [
                    {
                        "currency": euro["pk"],
                        "quantity": "120.00000",
                    }
                ],
            },
            {
                "period": flow_report_opts["periods"][1],
                "moneys": [
                    {
                        "currency": euro["pk"],
                        "quantity": "120.00000",
                    }
                ],
            },
        ]

        # Now we define a currency prices portifolio and run again
        currency_price_portifolio = [
            {
                "currency": euro["code"],
                "prices": [
                    {"date": "2019-06-15", "price": 2},
                    {"date": "2019-06-17", "price": 2},
                    {"date": "2019-07-01", "price": 3},
                ],
            },
            {
                "currency": real["code"],
                "prices": [
                    {"date": "2019-06-15", "price": 0.5},
                    {"date": "2019-06-17", "price": 0.5},
                    {"date": "2019-07-01", "price": 0.75},
                ],
            },
        ]
        flow_report_opts = {
            **flow_report_opts,
            "currency_opts": {
                "price_portifolio": currency_price_portifolio,
                "convert_to": real["code"],
            },
        }
        flow_report_data = self.trm.post_flow_evolution_report(flow_report_opts)

        # And revenues are ok
        revenues_data = TestHelpers.select_by(
            flow_report_data["data"],
            "account",
            revenue_acc["pk"],
        )
        assert revenues_data["flows"] == [
            {
                "period": flow_report_opts["periods"][0],
                "moneys": [
                    {
                        "currency": real["pk"],
                        # (-100 * 2 / 0.5) + (-450) = -850
                        "quantity": "-850.00000",
                    },
                ],
            },
            {"period": flow_report_opts["periods"][1], "moneys": []},
        ]

        # And so is expenses
        expenses_data = TestHelpers.select_by(
            flow_report_data["data"],
            "account",
            expenses_acc["pk"],
        )
        assert expenses_data["flows"] == [
            {
                "period": flow_report_opts["periods"][0],
                "moneys": [
                    {
                        "currency": real["pk"],
                        # 120 * 2 / 0.5 = 480
                        "quantity": "480.00000",
                    },
                ],
            },
            {
                "period": flow_report_opts["periods"][1],
                "moneys": [
                    {
                        "currency": real["pk"],
                        # 120 * 3 / 0.75 = 480
                        "quantity": "480.00000",
                    },
                ],
            },
        ]

    def test_get_exchange_rates(self):
        populate_exchangerates_with_mock_data()
        start_at = "2020-01-01"
        end_at = "2020-01-06"
        currency_codes = "BRL,EUR"
        params = {"start_at": start_at, "end_at": end_at, "currency_codes": currency_codes}
        res = self.trm.get_exchange_rates_data(params)
        # THE RESULT IS MOCKED!
        exp = [
            {
                "currency": "EUR",
                "prices": [
                    {"date": "2020-01-06", "price": 1.0},
                    {"date": "2020-01-03", "price": 1.0},
                    {"date": "2020-01-02", "price": 1.0},
                    {"date": "2020-01-01", "price": 1.0},
                    {"date": "2020-01-05", "price": 1.0},
                    {"date": "2020-01-04", "price": 1.0},
                ],
            },
            {
                "currency": "BRL",
                "prices": [
                    {"date": "2020-01-06", "price": 1 / 5},
                    {"date": "2020-01-03", "price": 1 / 4},
                    {"date": "2020-01-02", "price": 1 / 4},
                    {"date": "2020-01-01", "price": 1 / 4},
                    {"date": "2020-01-05", "price": 1 / 4},
                    {"date": "2020-01-04", "price": 1 / 4},
                ],
            },
        ]

        exp_currencies = set(x["currency"] for x in exp)
        res_currencies = set(x["currency"] for x in res)
        assert exp_currencies == res_currencies

        for currency in exp_currencies:
            exp_prices = next(x["prices"] for x in exp if x["currency"] == currency)
            res_prices = next(x["prices"] for x in res if x["currency"] == currency)

            sorted_exp_prices = sorted(exp_prices, key=(lambda x: x["date"]))
            sorted_res_prices = sorted(res_prices, key=(lambda x: x["date"]))

            assert sorted_exp_prices == sorted_res_prices

    def test_create_movement_with_comment(self):
        # Currencies setup
        euro = TestHelpers.select_by(self.trm.get_currencies(), "name", "Euro")

        # Accounts setup
        current_acc = self.trm.post_account(self.data_maker.current_acc(self.root_acc))
        supermarket = self.trm.post_account(self.data_maker.supermarket_acc(self.root_acc))

        # A transaction with a comment in a movement
        transaction_data = self.data_maker.paid_supermarket(current_acc, supermarket, euro)
        comment = "Was expensive because of olive oil!"
        transaction_data["movements_specs"][0]["comment"] = comment

        result = self.trm.post_transaction(transaction_data)
        assert result["movements_specs"][0]["comment"] == comment

    def test_query_for_transaction_based_on_description(self):
        # Get Currency
        euro = TestHelpers.select_by(self.trm.get_currencies(), "name", "Euro")

        # Accounts setup
        assets = self.trm.post_account(self.data_maker.assets_acc())
        bank = self.trm.post_account(self.data_maker.current_acc(assets))
        cash = self.trm.post_account(self.data_maker.money_acc(assets))

        # Creates two transactions
        deposit_1_data = self.data_maker.deposit(bank, cash, euro, "2020-01-01")
        deposit_1_data["reference"] = "The first deposit!"
        deposit_1 = self.trm.post_transaction(deposit_1_data)

        deposit_2_data = self.data_maker.deposit(bank, cash, euro, "2020-01-02")
        deposit_2_data["reference"] = "The second deposit!"
        deposit_2 = self.trm.post_transaction(deposit_2_data)

        unrelated_data = self.data_maker.deposit(bank, cash, euro, "2020-01-02")
        unrelated_data["reference"] = "FOO"
        unrelated_data["description"] = "FOO"
        unrelated = self.trm.post_transaction(unrelated_data)

        # Query for the first one only
        result_1 = self.trm.get_transactions({"reference": "first", "description": "deposit"})
        assert len(result_1) == 1
        assert result_1[0] == deposit_1

        # Query for the second one only
        result_2 = self.trm.get_transactions({"reference": "second", "description": "deposit"})
        assert len(result_2) == 1
        assert result_2[0] == deposit_2

        # Query for both
        result_3 = self.trm.get_transactions({"description": "deposit"})
        assert len(result_3) == 2
        assert result_3[0] == deposit_2  # Most recent
        assert result_3[1] == deposit_1  # Most recent

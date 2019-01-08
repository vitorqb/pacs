from unittest.mock import patch, Mock
from common.test import PacsTestCase
from accounting.balance import Balance, Journal
from accounting.money import Money
from movements.models import Transaction
from currencies.tests.factories import CurrencyTestFactory, MoneyTestFactory


class BalanceTestCase(PacsTestCase):
    pass


class TestBalance(BalanceTestCase):

    def test_get_for_currency_empty(self):
        currency = CurrencyTestFactory()
        balance = Balance([])
        assert balance.get_for_currency(currency) == Money(0, currency)

    def test_get_for_currency_not_present_return_zero(self):
        currencies = CurrencyTestFactory.create_batch(2)
        money = Money(10, currencies[0])
        balance = Balance([money])
        assert balance.get_for_currency(currencies[1]) == Money(0, currencies[1])

    def test_get_for_currency_present_two_movements(self):
        currency = CurrencyTestFactory()
        moneys = [Money(10, currency), Money(20, currency)]
        balance = Balance(moneys)
        assert balance.get_for_currency(currency) == Money(30, currency)

    def test_get_for_currencies_multiple_currencies(self):
        currencies = CurrencyTestFactory.create_batch(2)
        moneys = [Money(10, currencies[0]), Money(-8, currencies[1])]
        balance = Balance(moneys)
        assert balance.get_for_currency(currencies[0]) == Money(10, currencies[0])
        assert balance.get_for_currency(currencies[1]) == Money(-8, currencies[1])

    def test_add_money_zero(self):
        money = MoneyTestFactory()
        balance = Balance([])
        assert balance.add_money(money) == Balance([money])

    def test_add_money_two_long(self):
        moneys = MoneyTestFactory.create_batch(2)
        balance = Balance([moneys[0]])
        assert balance.add_money(moneys[1]) == Balance(moneys)

    def test_get_currencies_base(self):
        currencies = CurrencyTestFactory.create_batch(2)
        balance = Balance([Money('11', currencies[0]), Money('7', currencies[1])])
        assert balance.get_currencies() == set(currencies)

    def test_equal_true(self):
        currency = CurrencyTestFactory()
        one = Balance([Money('10', currency)])
        two = Balance([Money('7', currency), Money('3', currency)])
        assert one == two

    def test_equal_false_diff_currencies(self):
        currencies = CurrencyTestFactory.create_batch(2)
        one = Balance([Money('10', currencies[0])])
        two = Balance([Money('10', currencies[1])])
        assert one != two

    def test_equal_false_diff_quantities(self):
        currency = CurrencyTestFactory()
        one = Balance([Money('10', currency)])
        two = Balance([Money('9', currency)])
        assert one != two


class TestJournal(BalanceTestCase):

    def test_get_balances(self):
        currency_one, currency_two = Mock(), Mock()
        transactions = [Mock(), Mock()]
        transactions[0].get_moneys_for_account.return_value =\
            [Money('10', currency_one)]
        transactions[1].get_moneys_for_account.return_value =\
            [Money('20', currency_one)]
        initial_balance = Balance([Money('20', currency_two)])

        journal = Journal(Mock(), initial_balance, transactions)

        result = journal.get_balances()
        assert result[0] == initial_balance.add_money(Money('10', currency_one))
        assert result[1] == result[0].add_money(Money('20', currency_one))

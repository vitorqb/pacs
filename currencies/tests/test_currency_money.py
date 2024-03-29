from decimal import Decimal
from unittest.mock import Mock

from common.testutils import PacsTestCase
from currencies.money import Balance, Money, MoneyAggregator

from .factories import MoneyTestFactory


class MoneyTestCase(PacsTestCase):
    pass


class TestMoney(MoneyTestCase):
    def test_base(self):
        currency = Mock()
        money = Money("10.24", currency)
        assert money.quantity == Decimal("10.24")
        assert money.currency == currency

    def test_sum(self):
        currency = Mock()
        money_one = MoneyTestFactory(quantity=1, currency=currency)
        money_two = MoneyTestFactory(quantity=2, currency=currency)
        assert money_one + money_two == Money(quantity=3, currency=currency)

    def test_different_currencies_raises_error(self):
        currencies = [Mock(), Mock()]
        moneys = [MoneyTestFactory(currency=c) for c in currencies]
        with self.assertRaises(ValueError):
            moneys[0] + moneys[1]


class TestMoneyAggregator:
    def test_empty(self):
        money_aggregator = MoneyAggregator()
        assert money_aggregator.get_moneys() == []

    def test_one_long(self):
        currency = Mock()
        money = MoneyTestFactory(currency=currency)
        money_aggregator = MoneyAggregator()
        money_aggregator.append_money(money)
        assert money_aggregator.get_moneys() == [money]

    def test_two_different_currencies(self):
        currencies = [Mock(), Mock()]
        moneys = [MoneyTestFactory(currency=c) for c in currencies]
        money_aggregator = MoneyAggregator()
        for money in moneys:
            money_aggregator.append_money(money)
        assert money_aggregator.get_moneys() == moneys

    def test_aggregates_if_same_currency(self):
        currencies = [Mock(), Mock()]
        same_currency_moneys = MoneyTestFactory.create_batch(2, currency=currencies[0])
        other_currency_money = MoneyTestFactory(currency=currencies[1])
        money_aggregator = MoneyAggregator()
        for money in [*same_currency_moneys, other_currency_money]:
            money_aggregator.append_money(money)
        assert money_aggregator.get_moneys() == [
            same_currency_moneys[0] + same_currency_moneys[1],
            other_currency_money,
        ]


class TestBalance(MoneyTestCase):
    def test_get_for_currency_empty(self):
        currency = Mock()
        balance = Balance([])
        assert balance.get_for_currency(currency) == Money(0, currency)

    def test_get_for_currency_not_present_return_zero(self):
        currencies = [Mock(), Mock()]
        money = Money(10, currencies[0])
        balance = Balance([money])
        assert balance.get_for_currency(currencies[1]) == Money(0, currencies[1])

    def test_get_for_currency_present_two_movements(self):
        currency = Mock()
        moneys = [Money(10, currency), Money(20, currency)]
        balance = Balance(moneys)
        assert balance.get_for_currency(currency) == Money(30, currency)

    def test_get_for_currencies_multiple_currencies(self):
        currencies = [Mock(), Mock()]
        moneys = [Money(10, currencies[0]), Money(-8, currencies[1])]
        balance = Balance(moneys)
        assert balance.get_for_currency(currencies[0]) == Money(10, currencies[0])
        assert balance.get_for_currency(currencies[1]) == Money(-8, currencies[1])

    def test_add_money_zero(self):
        money = Mock(quantity=Decimal("10"))
        balance = Balance([])
        assert balance.add_money(money) == Balance([money])

    def test_add_money_two_long(self):
        moneys = [Mock(quantity=Decimal(5)), Mock(quantity=Decimal(2))]
        balance = Balance([moneys[0]])
        assert balance.add_money(moneys[1]) == Balance(moneys)

    def test_get_currencies_base(self):
        currencies = [Mock(), Mock()]
        balance = Balance([Money("11", currencies[0]), Money("7", currencies[1])])
        assert balance.get_currencies() == set(currencies)

    def test_equal_true(self):
        currency = Mock()
        one = Balance([Money("10", currency)])
        two = Balance([Money("7", currency), Money("3", currency)])
        assert one == two

    def test_equal_empty_and_not_empty(self):
        currency = Mock()
        one = Balance([])
        two = Balance([Money("10", currency)])
        assert one != two

    def test_equal_false_diff_currencies(self):
        currencies = [Mock(), Mock()]
        one = Balance([Money("10", currencies[0])])
        two = Balance([Money("10", currencies[1])])
        assert one != two

    def test_equal_false_diff_quantities(self):
        currency = Mock()
        one = Balance([Money("10", currency)])
        two = Balance([Money("9", currency)])
        assert one != two

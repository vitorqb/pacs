from __future__ import annotations

from copy import copy
from decimal import Decimal
from typing import TYPE_CHECKING, List, Set

import attr

from common.utils import decimals_equal

if TYPE_CHECKING:
    from currencies.models import Currency


@attr.s(frozen=True, eq=False)
class Money:
    """A combination of a quantity and a currency."""

    quantity: Decimal = attr.ib(converter=Decimal)
    currency: Currency = attr.ib()

    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return self.currency == other.currency and decimals_equal(self.quantity, other.quantity)

    def __add__(self, other):
        if not isinstance(other, Money):
            raise TypeError("Can only sum Money")
        if not self.currency == other.currency:
            raise ValueError("Can not sum Moneys from different currencies.")
        return attr.evolve(self, quantity=self.quantity + other.quantity)


@attr.s()
class MoneyAggregator:
    """
    Used to aggregate moneys. Maintains a list of moneys with at max one money
    per currency. When appending a new money, if there is already a money in
    the list for that currency, sum then instead of appending.
    """

    _moneys: List[Money] = attr.ib(factory=list, init=False)
    _currencies_set: Set[Currency] = attr.ib(factory=set, init=False)

    def append_money(self, money: Money) -> None:
        """
        Appends money to the internal list.
        If there is already a money for this currency, sum them.
        If not, just append money.
        """
        currency = money.currency
        if currency not in self._currencies_set:
            self._moneys.append(money)
            self._currencies_set.add(currency)
            return
        for i, _ in enumerate(self._moneys):
            if self._moneys[i].currency == currency:
                self._moneys[i] += money
                return
        raise RuntimeError("Something went really wrong.")

    def get_moneys(self) -> List[Money]:
        return copy(self._moneys)

    def as_balance(self) -> Balance:
        return Balance(self.get_moneys())


@attr.s(frozen=True, eq=False)
class Balance:
    """An aggregation of Money from different currencies"""

    _moneys: List[Money] = attr.ib()

    def get_for_currency(self, currency: Currency) -> Money:
        """Returns the Money representing the Balance for a specific currency"""
        quantity = Decimal("0")
        for m in (m for m in self._moneys if m.currency == currency):
            quantity += m.quantity
        return Money(quantity, currency)

    def add_money(self, money: Money) -> Balance:
        """Returns a new balance with money added."""
        return attr.evolve(self, moneys=[*self._moneys, money])

    def add_moneys(self, moneys: List[Money]) -> Balance:
        out = self
        for money in moneys:
            out = out.add_money(money)
        return out

    def get_currencies(self) -> Set[Currency]:
        """Returns a set with all the currencies for this Balance"""
        return set(x.currency for x in self._moneys)

    def get_moneys(self) -> List[Money]:
        """Returns a list of Money, one ofr each currency of self."""
        return [self.get_for_currency(c) for c in self.get_currencies()]

    def __add__(self, other: object) -> Balance:
        assert isinstance(other, Balance)
        return self.add_moneys(other._moneys)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Balance):
            return False
        currencies = self.get_currencies()
        if currencies != other.get_currencies():
            return False
        for currency in self.get_currencies():
            if self.get_for_currency(currency) != other.get_for_currency(currency):
                return False
        return True

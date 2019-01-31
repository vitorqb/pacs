from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List, Set

import attr

from common.utils import decimals_equal

if TYPE_CHECKING:
    from currencies.models import Currency


@attr.s(frozen=True, cmp=False)
class Money():
    """ A combination of a quantity and a currency. """
    quantity: Decimal = attr.ib(converter=Decimal)
    currency: Currency = attr.ib()

    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return (
            self.currency == other.currency and
            decimals_equal(self.quantity, other.quantity)
        )


@attr.s(frozen=True, cmp=False)
class Balance:
    """ An aggregation of Money from different currencies """
    _moneys: List[Money] = attr.ib()

    def get_for_currency(self, currency: Currency) -> Money:
        """ Returns the Money representing the Balance for a specific currency """
        quantity = Decimal('0')
        for m in (m for m in self._moneys if m.currency == currency):
            quantity += m.quantity
        return Money(quantity, currency)

    def add_money(self, money: Money) -> Balance:
        """ Returns a new balance with money added. """
        return attr.evolve(self, moneys=[*self._moneys, money])

    def add_moneys(self, moneys: List[Money]) -> Balance:
        out = self
        for money in moneys:
            out = out.add_money(money)
        return out

    def get_currencies(self) -> Set[Currency]:
        """ Returns a set with all the currencies for this Balance """
        return set(x.currency for x in self._moneys)

    def get_moneys(self) -> List[Money]:
        """ Returns a list of Money, one ofr each currency of self. """
        return [
            self.get_for_currency(c) for c in self.get_currencies()
        ]

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

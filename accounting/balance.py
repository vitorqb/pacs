from __future__ import annotations
import attr
from decimal import Decimal
from typing import TYPE_CHECKING, List, Set
from .money import Money

if TYPE_CHECKING:
    from currencies.models import Currency
    from accounts.models import Account
    from movements.models import Transaction


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
        for currency in self.get_currencies():
            if self.get_for_currency(currency) != other.get_for_currency(currency):
                return False
        return True


@attr.s(frozen=True)
class Journal:
    """ Represents a history of transactions for an account """

    account: Account = attr.ib()
    # initial_balance is the balance before the first transaction.
    initial_balance: Balance = attr.ib()
    # An iterable of all Transaction for this journal. Must be transactions
    # that include account.
    transactions: List[Transaction] = attr.ib()

    def get_balances(self) -> List[Balance]:
        """ Returns a list with the same length as transactions, showing the
        Balance for the account after the transaction. """
        out = []
        current_balance = Balance([])
        for transaction in self.transactions:
            moneys = transaction.get_moneys_for_account(self.account)
            current_balance = current_balance.add_moneys(moneys)
            out.append(current_balance)
        return out

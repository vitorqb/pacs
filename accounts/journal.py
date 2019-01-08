from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List

import attr

from currencies.money import Balance

if TYPE_CHECKING:
    from accounts.models import Account
    from movements.models import Transaction


@attr.s(frozen=True)
class Journal:
    """ Represents a history of transactions for an account """

    account: Account = attr.ib()

    # initial_balance is the balance before the first transaction.
    initial_balance: Balance = attr.ib()

    # An iterable of all Transaction for this journal. Must be transactions
    # that include account.
    transactions: Iterable[Transaction] = attr.ib()

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

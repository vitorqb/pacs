from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List

import attr

from currencies.money import Balance

if TYPE_CHECKING:
    from accounts.models import Account
    from movements.models import TransactionQuerySet, Transaction


@attr.s(frozen=True)
class Journal:
    """ Represents an ordered sequence (history) of balances for an account """

    account: Account = attr.ib()

    # initial_balance is the balance before the first transaction.
    initial_balance: Balance = attr.ib()

    # An iterable of all Transaction for this journal.
    transactions: TransactionQuerySet = attr.ib()

    def __attrs_post_init__(self):
        # Prepares transactions by filtering/prefetching/ordering
        # !!!! TODO -> Should sort by -date, id
        transactions = self\
            .transactions\
            .filter_by_account(self.account)\
            .prefetch_related(
                "movement_set__currency",
                "movement_set__account__acc_type"
            )\
            .order_by('date', 'id')\
            .distinct()
        object.__setattr__(self, 'transactions', transactions)

    def get_balances(self) -> List[Balance]:
        """ Returns a list with the same length as transactions, showing the
        Balance for the account after the transaction. """
        out = []
        # !!!! TODO -> Shouldn't this be self.initial_balance ?
        current_balance = Balance([])
        for transaction in self.transactions:
            moneys = transaction.get_moneys_for_account(self.account)
            current_balance = current_balance.add_moneys(moneys)
            out.append(current_balance)
        return out

    def get_balance_before_transaction(self, transaction: Transaction) -> Balance:
        """ Returns the balance exactly before a transaction. """
        moneys = self.initial_balance.get_moneys()
        moneys += self\
            .transactions\
            .filter_before_transaction(transaction)\
            .get_moneys_for_account(self.account)
        return Balance(moneys)

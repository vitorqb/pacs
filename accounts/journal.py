from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List

import attr

from currencies.money import Balance

if TYPE_CHECKING:
    from accounts.models import Account
    from movements.models import TransactionQuerySet, Transaction


@attr.s(frozen=True)
class Journal:
    """ Represents a history of transactions for an account """

    account: Account = attr.ib()

    # initial_balance is the balance before the first transaction.
    initial_balance: Balance = attr.ib()

    # An iterable of all Transaction for this journal. Must be transactions
    # that include account and must be ordered by ('date', 'id').
    # !!!! TODO -> This should not assume it is sorted, but should sort it instead
    # !!!!         and should sort by ('-date', 'id')
    # !!!! TODO -> This should not assume it is filtered by account, but should
    # !!!!         actually filter it instead!
    transactions: TransactionQuerySet = attr.ib()

    def get_balances(self) -> List[Balance]:
        """ Returns a list with the same length as transactions, showing the
        Balance for the account after the transaction. """
        out = []
        # !!!! TODO -> Shouldn't this be self.initial_balance ?
        current_balance = Balance([])
        # !!!! TODO -> Does iterator kills prefetching?
        for transaction in self.transactions.iterator():
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

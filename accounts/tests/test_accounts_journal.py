from unittest.mock import Mock

from accounts.journal import Journal
from common.test import PacsTestCase
from currencies.money import Balance, Money


class BalanceTestCase(PacsTestCase):
    pass


class TestJournal(PacsTestCase):

    def gen_transaction_mock(self, money_for_account):
        transaction = Mock()
        transaction.get_moneys_for_account.return_value = money_for_account
        return transaction

    def test_iter(self):
        currency_one, currency_two = Mock(), Mock()
        m_transactions_qset = Mock()
        m_transactions_qset.iterator.return_value = [
            self.gen_transaction_mock([Money('10', currency_one)]),
            self.gen_transaction_mock([Money('20', currency_two)])
        ]
        initial_balance = Balance([Money('20', currency_two)])

        journal = Journal(Mock(), initial_balance, m_transactions_qset)

        result = journal.get_balances()
        assert result[0] == initial_balance.add_money(Money('10', currency_one))
        assert result[1] == result[0].add_money(Money('20', currency_two))

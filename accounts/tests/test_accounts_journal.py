from datetime import date, timedelta
from unittest.mock import Mock, MagicMock

from accounts.journal import Journal
from accounts.tests.factories import AccountTestFactory
from common.models import list_to_queryset
from common.test import PacsTestCase, MockQset
from currencies.money import Balance, Money
from currencies.tests.factories import MoneyTestFactory
from movements.tests.factories import TransactionTestFactory


class BalanceTestCase(PacsTestCase):
    pass


class TestJournal(PacsTestCase):

    def gen_transaction_mock(self, money_for_account):
        transaction = Mock()
        transaction.get_balance_for_account.return_value = \
            Balance(money_for_account)
        return transaction

    def test_iter(self):
        currency_one, currency_two = Mock(), Mock()
        m_transactions_qset = MockQset()
        m_transactions_qset.set_iter([
            self.gen_transaction_mock([Money('10', currency_one)]),
            self.gen_transaction_mock([Money('20', currency_two)])
        ])
        initial_balance = Balance([Money('20', currency_two)])

        journal = Journal(Mock(), initial_balance, m_transactions_qset)

        result = journal.get_balances()
        assert result[0] == initial_balance.add_money(Money('10', currency_one))
        assert result[1] == result[0].add_money(Money('20', currency_two))

    def test_process_transactions_on_init(self):
        m_transactions_qset, m_account = MockQset(), Mock()
        journal = Journal(m_account, Mock(), transactions=m_transactions_qset)
        assert m_transactions_qset.filter_by_account_args == (m_account,)
        assert m_transactions_qset.prefetch_related_args == (
            "movement_set__currency",
            "movement_set__account__acc_type"
        )
        assert m_transactions_qset.order_by_args == ('date', 'id')
        assert m_transactions_qset.distinct_called
        assert journal.transactions == m_transactions_qset\
            .filter_by_account()\
            .prefetch_related()\
            .order_by()\
            .distinct()

    def test_integration_get_balance_before_transaction(self):
        self.populate_accounts()
        self.populate_currencies()

        # Set up an account
        acc = AccountTestFactory()  # <- we want balance for this

        # And some dates
        target_date = date(2018, 1, 1)
        date_before = target_date - timedelta(days=1)

        # A transaction before that should count
        transaction_before = TransactionTestFactory(
            movements_specs__0__account=acc,
            date_=date_before
        )

        # A transaction at the same date that should count (pk lower)
        transaction_same_date_pk_lower = TransactionTestFactory(
            movements_specs__0__account=acc,
            date_=target_date
        )

        # The targeted transaction
        transaction_targeted = TransactionTestFactory(
            movements_specs__0__account=acc,
            date_=target_date
        )
        assert transaction_targeted.pk > transaction_same_date_pk_lower.pk

        # A transaction at the same date that should not count (pk higher)
        transaction_same_date_pk_higher = TransactionTestFactory(
            movements_specs__0__account=acc,
            date_=target_date
        )
        assert transaction_targeted.pk < transaction_same_date_pk_higher.pk

        # An initial balance
        initial_balance = Balance([MoneyTestFactory()])

        # Makes the journal
        transactions_qset = list_to_queryset([
            transaction_before,
            transaction_same_date_pk_lower,
            transaction_targeted,
            transaction_same_date_pk_higher
        ]).order_by('date', 'id')
        journal = Journal(acc, initial_balance, transactions_qset)

        # Calculates expected result
        exp_result = initial_balance
        for transaction in [
                transaction_before,
                transaction_same_date_pk_lower,
        ]:
            exp_result += transaction.get_balance_for_account(acc)
        result = journal.get_balance_before_transaction(transaction_targeted)
        assert result == exp_result

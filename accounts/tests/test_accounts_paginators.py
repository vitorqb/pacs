from unittest.mock import Mock, call, patch, MagicMock

from accounts.journal import Journal
from accounts.paginators import (JournalAllPaginator, JournalPagePaginator,
                                 get_journal_paginator)
from accounts.tests.factories import AccountTestFactory
from common.test import PacsTestCase, MockQset
from common.models import list_to_queryset
from currencies.money import Balance
from movements.tests.factories import TransactionTestFactory
from movements.models import Transaction


class Test_get_journal_paginator(PacsTestCase):

    def test_with_page_and_page_size_returns_JournalPagePaginator(self):
        request = Mock(query_params={
            'page': 1,
            'page_size': 1
        })
        paginator = get_journal_paginator(request, Mock())
        assert isinstance(paginator, JournalPagePaginator)

    def test_with_page_size_only_returns_JournalPagePaginator(self):
        request = Mock(query_params={'page_size': 1})
        paginator = get_journal_paginator(request, Mock())
        assert isinstance(paginator, JournalPagePaginator)

    def test_with_page_only_returns_JournalAllPaginator(self):
        request = Mock(query_params={'page': 1})
        paginator = get_journal_paginator(request, Mock())
        assert isinstance(paginator, JournalAllPaginator)


class TestJournalAllPaginator(PacsTestCase):

    @patch('accounts.paginators.JournalSerializer')
    def test_get_data_simple_returns_serialized_journal(self, m_JournalSerializer):
        """ JournalAllPaginator should not do any pagination, only return the
        serialized Journal """
        m_request, m_journal = Mock(), Mock()
        serializer = JournalAllPaginator(m_request, m_journal)
        data = serializer.get_data()
        assert m_JournalSerializer.call_count == 1
        assert m_JournalSerializer.call_args == call(m_journal)
        assert data == m_JournalSerializer().data


class TestJournalPagePaginator(PacsTestCase):

    def setUp(self):
        """ Prepares a paginator with all arguments mocked """
        self.m_request = Mock()
        self.m_journal = Mock(transactions=MockQset())
        self.m_base_paginator = MagicMock()
        self.paginator = JournalPagePaginator(
            self.m_request,
            self.m_journal,
            self.m_base_paginator
        )

        # Patches the JournalSerializer so we don't try to serialize a Mock() obj
        patcher_JournalSerializer = patch('accounts.paginators.JournalSerializer')
        self.m_JournalSerializer = patcher_JournalSerializer.start()
        self.m_JournalSerializer.return_value.return_value = {'a': 'b'}
        self.addCleanup(patcher_JournalSerializer.stop)

    def test_get_data_returns_count_of_transactions_from_base_paginator(self):
        data = self.paginator.get_data()
        assert data['count'] == self.m_base_paginator.page.paginator.count

    def test_get_data_returns_previous_page_from_base_paginator(self):
        data = self.paginator.get_data()
        # The method that should have been called
        m_get_previous_link = self.m_base_paginator.get_previous_link
        assert data['previous'] == m_get_previous_link.return_value
        assert m_get_previous_link.call_count == 1
        assert m_get_previous_link.call_args == call()

    def test_get_data_returns_next_page_from_base_paginator(self):
        data = self.paginator.get_data()
        # The method that should have been called
        m_get_next_link = self.m_base_paginator.get_next_link
        assert data['next'] == m_get_next_link.return_value
        assert m_get_next_link.call_count == 1
        assert m_get_next_link.call_args == call()

    @patch('accounts.paginators.JournalPagePaginator.paginate_journal')
    def test_get_data_serializes_correct_journal(self, m_paginate_journal):
        data = self.paginator.get_data()

        # The serialized journal should be the one generated by paginate_journal
        assert data['journal'] == self.m_JournalSerializer.return_value.data
        assert self.m_JournalSerializer.call_count == 1
        assert self.m_JournalSerializer.call_args == \
            call(m_paginate_journal.return_value)

        # And m_paginate_journal should have been called once with journal and
        # the paginated transaction qset
        assert m_paginate_journal.call_count == 1
        assert m_paginate_journal.call_args == \
            call(self.m_journal, self.m_base_paginator.paginate_queryset())

    def test_paginate_journal_integration_base(self):
        # Creates an account and transactions for it
        self.populate_accounts()
        account = AccountTestFactory()
        transactions = TransactionTestFactory.create_batch(
            8,
            movements_specs__0__account=account
        )
        transactions_qset = list_to_queryset(transactions).order_by('date', 'id')

        # And a complete account journal
        journal = Journal(account, Balance([]), transactions_qset)

        # Lets get a new qset with transactions 3-6, inclusive
        transactions_qset_page = transactions_qset[2:6]

        # And the paginated journal
        journal_page = JournalPagePaginator.paginate_journal(
            journal,
            transactions_qset_page
        )

        # The new journal should have as initial balance the balance after
        # the two first transactions
        exp_initial_balance = Balance([])
        for transaction in transactions_qset[0:2]:
            moneys = transaction.get_moneys_for_account(account)
            exp_initial_balance = exp_initial_balance.add_moneys(moneys)
        assert exp_initial_balance == journal_page.initial_balance

        # And should have the 4 middle transactions
        exp_transactions_ids = transactions_qset_page.values_list('pk', flat=True)
        resp_transactions_ids = journal_page.transactions.values_list(
            'pk', flat=True)
        assert list(exp_transactions_ids) == list(resp_transactions_ids)

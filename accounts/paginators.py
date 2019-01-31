"""
Implements paginators specifically for Journals.
"""
from __future__ import annotations

from typing import List

import attr
from rest_framework.pagination import PageNumberPagination

from accounts.journal import Journal
from accounts.serializers import JournalSerializer
from movements.models import Transaction


def get_journal_paginator(request, journal):
    """ Factory method that returns a Paginator to use for journal
    given a request. """
    # Returns real paginator if page_size is present, if not returns the dummy
    # JournalAllPaginator
    if 'page_size' in request.query_params:
        return JournalPagePaginator(request, journal)
    return JournalAllPaginator(request, journal)


#
# Journal paginators: paginate journals by splitting the TransactionQuerySet
#     they use and setting the appropriate initial balance.
#
@attr.s()
class JournalAllPaginator:
    """ A fake paginator, that just serializes and returns, but implements
    the paginator interface."""

    request = attr.ib()
    journal = attr.ib()

    def get_data(self):
        """ Simply returns the serialized journal, with no pagination """
        serializer = JournalSerializer(self.journal)
        return serializer.data


@attr.s()
class JournalPagePaginator:
    """ A paginator by page, that uses an PageNumberPagination under the hoods """
    _BASE_PAGINATOR_DEFAULT_CLASS = type(
        '_Paginator',
        (PageNumberPagination,),
        {'page_query_param': 'page',
         'page_size_query_param': 'page_size'}
    )

    request = attr.ib()
    journal = attr.ib()
    # base_paginator is used under the hood to actually perform the pagination
    _base_paginator = attr.ib(factory=_BASE_PAGINATOR_DEFAULT_CLASS)

    def get_data(self):
        """ Paginates the journal and returns. The returning dict contains a
        journal with the correct transactions and balances, together with pagination
        info similar to PageNumberPagination """
        transactions_qset = self.journal.transactions
        transactions_page = self._base_paginator.paginate_queryset(
            transactions_qset,
            self.request
        )
        paged_journal = self.paginate_journal(self.journal, transactions_page)
        serializer = JournalSerializer(paged_journal)
        return {
            'count': self._base_paginator.page.paginator.count,
            'previous': self._base_paginator.get_previous_link(),
            'next': self._base_paginator.get_next_link(),
            'journal': serializer.data
        }

    @staticmethod
    def paginate_journal(
            journal: Journal,
            transactions_page: List[Transaction],
    ) -> Journal:
        """ Returns a new Journal for the same account representing
        only the transactions on transactions_page.
        Assumes that:
          - Both `transactions_page` is ordered by (date, id).
          - transactions_page is a continuous slice of
            journal.transactions """
        try:
            first_transaction = transactions_page[0]
        except IndexError:
            first_transaction = None
        initial_balance = journal.get_balance_before_transaction(first_transaction)
        # Journal expects a TransactionQuerySet, not a list. So we hack it here
        # a bit. Inneficient but simplifies our life.
        transactions_qset = journal.transactions.filter(
            pk__in=(x.pk for x in transactions_page)
        )
        return Journal(journal.account, initial_balance, transactions_qset)

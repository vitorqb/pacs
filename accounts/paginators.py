"""
Implements paginators specifically for Journals.
"""
from __future__ import annotations

from copy import copy
from typing import List

import attr
from rest_framework.pagination import PageNumberPagination

from accounts.journal import Journal
from accounts.serializers import JournalSerializer
from common.constants import PAGE_QUERY_PARAM, PAGE_SIZE_QUERY_PARAM
from movements.models import Transaction


def get_journal_paginator(request, journal):
    """Factory method that returns a Paginator to use for journal
    given a request."""
    # Returns real paginator if page_size is present, if not returns the dummy
    # JournalAllPaginator
    if PAGE_SIZE_QUERY_PARAM in request.query_params:
        return JournalPagePaginator(request, journal)
    return JournalAllPaginator(request, journal)


#
# Journal paginators: paginate journals by splitting the TransactionQuerySet
#     they use and setting the appropriate initial balance.
#
@attr.s()
class JournalAllPaginator:
    """A fake paginator, that just serializes and returns, but implements
    the paginator interface."""

    request = attr.ib()
    journal = attr.ib()

    def get_data(self, reverse=False):
        """Simply returns the serialized journal, with no pagination"""
        serializer = JournalSerializer(self.journal)
        journal_data = serializer.data
        if reverse:
            journal_data = _reversed_journal_data(journal_data)
        return journal_data


@attr.s()
class JournalPagePaginator:
    """A paginator by page, that uses an PageNumberPagination under the hoods"""

    _BASE_PAGINATOR_DEFAULT_CLASS = type(
        "_Paginator",
        (PageNumberPagination,),
        {"page_query_param": PAGE_QUERY_PARAM, "page_size_query_param": PAGE_SIZE_QUERY_PARAM},
    )

    request = attr.ib()
    journal = attr.ib()
    # base_paginator is used under the hood to actually perform the pagination
    _base_paginator = attr.ib(factory=_BASE_PAGINATOR_DEFAULT_CLASS)

    def get_data(self, reverse=False):
        """Paginates the journal and returns. The returning dict contains a
        journal with the correct transactions and balances, together with pagination
        info similar to PageNumberPagination"""
        transactions_qset = self.journal.transactions
        if reverse:
            transactions_qset = transactions_qset.reverse()
        transactions_page = self._base_paginator.paginate_queryset(transactions_qset, self.request)
        paged_journal = self.paginate_journal(self.journal, transactions_page)
        serializer = JournalSerializer(paged_journal)
        journal_data = serializer.data
        if reverse:
            journal_data = _reversed_journal_data(serializer.data)
        return {
            "count": self._base_paginator.page.paginator.count,
            "previous": self._base_paginator.get_previous_link(),
            "next": self._base_paginator.get_next_link(),
            "journal": journal_data,
        }

    @staticmethod
    def paginate_journal(
        journal: Journal,
        transactions_page: List[Transaction],
    ) -> Journal:
        """Returns a new Journal for the same account representing
        only the transactions on transactions_page."""
        if len(transactions_page) == 0:
            # No transactions -> Just count initial balance
            return Journal(journal.account, journal.initial_balance, journal.transactions.none())
        first_transaction = min(transactions_page, key=lambda x: (x.date, x.pk))
        initial_balance = journal.get_balance_before_transaction(first_transaction)
        # Journal expects a TransactionQuerySet, not a list. So we hack it here
        # a bit. Inneficient but simplifies our life.
        transactions_qset = journal.transactions.filter(pk__in=(x.pk for x in transactions_page))
        return Journal(journal.account, initial_balance, transactions_qset)


def _reversed_journal_data(data):
    """Reverts the ordering of transactions and balances in the data for
    a serialized Journal"""
    out = copy(data)
    for key_to_revert in ("transactions", "balances"):
        out[key_to_revert] = out[key_to_revert][::-1]
    return out

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.journal import Journal
from accounts.models import Account
from accounts.serializers import AccountSerializer, JournalSerializer
from accounts.paginators import get_journal_paginator
from currencies.money import Balance
from movements.models import Transaction


class AccountViewSet(ModelViewSet):
    queryset = Account.objects.all().prefetch_related("acc_type")
    serializer_class = AccountSerializer

    @action(['get'], True)
    def journal(self, request, pk=None):
        account = self.get_object()
        journal = Journal(account, Balance([]), _get_all_transactions())
        paginator = get_journal_paginator(request, journal)
        data = paginator.get_data()
        return Response(data)


def _get_all_transactions():
    """ Return all transactions. Separated maily to facilitate test mock. """
    return Transaction.objects.all()

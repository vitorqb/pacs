from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.journal import Journal
from accounts.models import Account
from accounts.serializers import AccountSerializer, JournalSerializer
from currencies.money import Balance
from movements.models import Transaction


class AccountViewSet(ModelViewSet):
    queryset = Account.objects.all().prefetch_related("acc_type")
    serializer_class = AccountSerializer

    @action(['get'], True)
    def journal(self, request, pk=None):
        account = self.get_object()
        journal = Journal(
            account,
            Balance([]),
            Transaction.objects.pre_process_for_journal()
        )
        serializer = JournalSerializer(journal)
        data = serializer.data
        return Response(data)

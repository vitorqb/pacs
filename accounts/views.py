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

        def get_transaction_base_qset():
            o = Transaction.objects
            o = o.prefetch_related(
                "movement_set__currency",
                "movement_set__account__acc_type"
            )
            o = o.order_by('date', 'pk')
            o = o.distinct()
            return o

        account = self.get_object()
        journal = Journal(
            account,
            Balance([]),
            get_transaction_base_qset().filter_by_account(account)
        )
        serializer = JournalSerializer(journal)
        data = serializer.data
        return Response(data)

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.models import Account
from accounts.serializers import AccountSerializer
from accounting.serializers import JournalSerializer
from accounting.balance import Journal, Balance
from movements.models import Transaction


class AccountViewSet(ModelViewSet):
    queryset = Account.objects.all().prefetch_related("acc_type")
    serializer_class = AccountSerializer

    @action(['get'], True)
    def journal(self, request, pk=None):
        transaction_qset = Transaction.objects.prefetch_related(
            "movement_set__currency",
            "movement_set__account__acc_type"
        )
        account = self.get_object()
        journal = Journal(
            account,
            Balance([]),
            transaction_qset.order_by('date').filter_by_account(account)
        )
        serializer = JournalSerializer(journal)
        data = serializer.data
        return Response(data)

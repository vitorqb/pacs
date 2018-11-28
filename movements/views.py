from rest_framework.viewsets import ModelViewSet
from movements.models import Transaction
from movements.serializers import TransactionSerializer


class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

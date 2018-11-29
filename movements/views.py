from rest_framework.viewsets import ModelViewSet
from django_filters import rest_framework as filters

from movements.models import Transaction
from movements.serializers import TransactionSerializer
from movements.filters import TransactionFilterSet


class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.order_by('-date').all()
    serializer_class = TransactionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = TransactionFilterSet

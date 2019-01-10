from rest_framework.viewsets import ModelViewSet
from django_filters import rest_framework as filters

from movements.models import Transaction
from movements.serializers import TransactionSerializer
from movements.filters import TransactionFilterSet


def _get_transaction_qset():
    out = Transaction.objects.all()
    out = out.order_by('-date', '-pk')
    out = out.prefetch_related(
        'movement_set',
        'movement_set__account',
        'movement_set__account__acc_type',
        'movement_set__currency'
    )
    return out


class TransactionViewSet(ModelViewSet):
    queryset =_get_transaction_qset()
    serializer_class = TransactionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = TransactionFilterSet

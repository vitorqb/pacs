from django_filters import rest_framework as filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import ModelViewSet

from common.constants import PAGE_QUERY_PARAM, PAGE_SIZE_QUERY_PARAM
from movements.filters import TransactionFilterSet
from movements.models import Transaction
from movements.serializers import TransactionSerializer


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

    pagination_class = type(
        '_Paginator',
        (PageNumberPagination,),
        {'page_query_param': PAGE_QUERY_PARAM,
         'page_size_query_param': PAGE_SIZE_QUERY_PARAM}
    )

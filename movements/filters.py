from django_filters import rest_framework as f


class TransactionFilterSet(f.FilterSet):
    account_id = f.NumberFilter(
        field_name='movement',
        lookup_expr='account__id__exact'
    )

from django_filters import rest_framework as f

from accounts.models import Account


class TransactionFilterSet(f.FilterSet):
    account_id = f.NumberFilter(method='filter_account')
    reference = f.CharFilter(lookup_expr='icontains')
    description = f.CharFilter(lookup_expr='icontains')

    def filter_account(self, queryset, name, account_id):
        """ Filters a Transaction Queryset by account_id, but
        considers the account plus all its descendants. """
        acc = Account.objects.filter(id=account_id).first()
        descendants_ids = (
            []
            if acc is None else
            acc.get_descendants_ids(True, use_cache=True)
        )
        return queryset\
            .filter(movement__account__id__in=list(descendants_ids))\
            .distinct()

from rest_framework.viewsets import ModelViewSet
from accounts.models import Account
from accounts.serializers import AccountSerializer


class AccountViewSet(ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

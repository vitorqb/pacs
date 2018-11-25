from rest_framework.viewsets import ModelViewSet
from .models import Currency
from .serializers import CurrencySerializer


class CurrencyViewSet(ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer

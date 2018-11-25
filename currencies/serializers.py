from rest_framework import serializers as s
from .models import Currency


class CurrencySerializer(s.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['pk', 'name', 'imutable']
        read_only_fields = ['pk', 'imutable']

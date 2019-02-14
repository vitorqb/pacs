from rest_framework import serializers

from accounts.models import Account
from accounts.serializers import BalanceSerializer
from reports.reports import BalanceEvolution, BalanceEvolutionQuery, Period


class PeriodField(serializers.Field):

    def to_internal_value(self, data):
        if not isinstance(data, list) or len(data) != 2:
            raise serializers.ValidationError(
                "Incorrect format: expectd a list of 2 dates."
            )
        return Period(
            serializers.DateField().to_internal_value(data[0]),
            serializers.DateField().to_internal_value(data[1])
        )

    def to_representation(self, period):
        return [
            serializers.DateField().to_representation(period.start),
            serializers.DateField().to_representation(period.end)
        ]


class BalanceEvolutionInputSerializer(serializers.Serializer):
    accounts = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        many=True
    )
    periods = serializers.ListSerializer(child=PeriodField())

    def get_data(self):
        self.is_valid(True)
        return self.validated_data


class BalanceEvolutionDataSerializer(serializers.Serializer):
    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all()
    )
    initial_balance = BalanceSerializer()
    balance_evolution = BalanceSerializer(many=True)


class BalanceEvolutionOutputSerializer(serializers.Serializer):
    periods = serializers.ListSerializer(child=PeriodField())
    data = serializers.ListSerializer(child=BalanceEvolutionDataSerializer())

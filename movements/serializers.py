from rest_framework.serializers import (ListSerializer, ModelSerializer,
                                        PrimaryKeyRelatedField, Serializer)

from accounts.models import Account
from currencies.money import Money
from currencies.serializers import MoneySerializer

from .models import MovementSpec, Transaction, TransactionFactory


class MovementSpecSerializer(Serializer):
    account = PrimaryKeyRelatedField(queryset=Account.objects.all())
    money = MoneySerializer()

    def create(self, validated_data):
        money_data = validated_data.pop('money')
        validated_data['money'] = Money(**money_data)
        return MovementSpec(**validated_data)


class TransactionSerializer(ModelSerializer):
    movements_specs = ListSerializer(
        child=MovementSpecSerializer(),
        source='get_movements_specs'
    )

    class Meta:
        model = Transaction
        fields = ['pk', 'description', 'reference', 'date', 'movements_specs']
        read_only_fields = ['pk']

    def create(self, validated_data):
        movements_data = validated_data.pop('get_movements_specs')
        validated_data['movements_specs'] = [
            MovementSpecSerializer().create(mov_data)
            for mov_data in movements_data
        ]
        validated_data['date_'] = validated_data.pop('date')
        return TransactionFactory()(**validated_data)

    def update(self, instance: Transaction, validated_data):
        if 'date' in validated_data:
            instance.set_date(validated_data['date'])
        if 'get_movements_specs' in validated_data:
            movements_data = validated_data.pop('get_movements_specs')
            movements = [
                MovementSpecSerializer().create(mov_data)
                for mov_data in movements_data
            ]
            instance.set_movements(movements)
        if 'description' in validated_data:
            instance.set_description(validated_data['description'])
        if 'reference' in validated_data:
            instance.set_reference(validated_data['reference'])
        return instance

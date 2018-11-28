from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    PrimaryKeyRelatedField,
    ListSerializer
)
from .models import Transaction, MovementSpec, TransactionFactory
from accounts.models import Account
from currencies.serializers import MoneySerializer
from currencies.money import Money
from currencies.models import Currency


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
        source='get_movements'
    )

    class Meta:
        model = Transaction
        # !!!! SMELL -> Change movements_specs -> movements?
        fields = ['pk', 'description', 'date', 'movements_specs']
        read_only_fields = ['pk']

    def is_valid(self, *args, **kwargs):
        super().is_valid(*args, **kwargs)

    def create(self, validated_data):
        movements_data = validated_data.pop('get_movements')
        validated_data['movements_specs'] = [
            MovementSpecSerializer().create(mov_data)
            for mov_data in movements_data
        ]
        validated_data['date_'] = validated_data.pop('date')
        return TransactionFactory()(**validated_data)

    def update(self, instance, validated_data):
        if 'date' in validated_data:
            instance.set_date(validated_data['date'])
        if 'get_movements' in validated_data:
            movements_data = validated_data.pop('get_movements')
            movements = [
                MovementSpecSerializer().create(mov_data)
                for mov_data in movements_data
            ]
            instance.set_movements(movements)
        if 'description' in validated_data:
            instance.set_description(validated_data['description'])
        return instance

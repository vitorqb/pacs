import rest_framework.serializers as serializers
from rest_framework.serializers import (
    ListSerializer,
    ModelSerializer,
    PrimaryKeyRelatedField,
    Serializer,
)

from accounts.models import Account
from currencies.money import Money
from currencies.serializers import MoneySerializer

from .models import MovementSpec, Transaction, TransactionFactory, TransactionTag


class MovementSpecSerializer(Serializer):
    account = PrimaryKeyRelatedField(queryset=Account.objects.all())
    money = MoneySerializer()
    comment = serializers.CharField(allow_blank=True, default="")

    def create(self, validated_data):
        money_data = validated_data.pop("money")
        validated_data["money"] = Money(**money_data)
        return MovementSpec(**validated_data)


class TransactionTagSerializer(ModelSerializer):
    class Meta:
        model = TransactionTag
        fields = ["name", "value"]


class TransactionSerializer(ModelSerializer):
    movements_specs = ListSerializer(child=MovementSpecSerializer(), source="get_movements_specs")
    tags = ListSerializer(
        child=TransactionTagSerializer(), source="get_tags", default=list, required=False
    )

    class Meta:
        model = Transaction
        fields = ["pk", "description", "reference", "date", "movements_specs", "tags"]
        read_only_fields = ["pk"]

    def create(self, validated_data):
        movements_data = validated_data.pop("get_movements_specs")
        validated_data["movements_specs"] = [
            MovementSpecSerializer().create(mov_data) for mov_data in movements_data
        ]
        validated_data["date_"] = validated_data.pop("date")
        tags_data = validated_data.pop("get_tags")
        validated_data["tags"] = [
            TransactionTag(name=x["name"], value=x["value"]) for x in tags_data
        ]
        return TransactionFactory()(**validated_data)

    def update(self, instance: Transaction, validated_data):
        if "date" in validated_data:
            instance.set_date(validated_data["date"])
        if "get_movements_specs" in validated_data:
            movements_data = validated_data.pop("get_movements_specs")
            movements = [MovementSpecSerializer().create(mov_data) for mov_data in movements_data]
            instance.set_movements(movements)
        if "description" in validated_data:
            instance.set_description(validated_data["description"])
        if "reference" in validated_data:
            instance.set_reference(validated_data["reference"])
        if "get_tags" in validated_data:
            tags_data = validated_data.pop("get_tags")
            tags = [TransactionTag(**d) for d in tags_data]
            instance.set_tags(tags)
        return instance

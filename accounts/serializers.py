from rest_framework.serializers import ModelSerializer, Field
from rest_framework.exceptions import ValidationError

from .models import Account, AccTypeEnum, AccountFactory


class AccTypeField(Field):
    """ Transforms a string into a value in AccTypeEnum """

    def to_internal_value(self, data):
        """ Transforms a string into an AccTypeEnum.
        `data` must be a string. The comparison is case insensitive. """
        if not isinstance(data, str):
            raise ValidationError("Expected a string")
        data = data.lower()
        for acc_type in AccTypeEnum:
            if data == acc_type.value.lower():
                return acc_type
        raise ValidationError(f"Unkown account type {data}")

    # !!!! TODO -> Really make this method
    def to_representation(self, value):
        return "Branch"


# !!!! TODO -> Make Serializer behave as we want it to
class AccountSerializer(ModelSerializer):
    acc_type = AccTypeField()

    class Meta:
        model = Account
        fields = ['pk', 'name', 'acc_type', 'parent']

    # !!!! TODO -> Make this method serious
    def create(self, validated_data):
        return AccountFactory()(**validated_data)

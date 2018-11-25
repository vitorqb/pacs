from rest_framework.serializers import ModelSerializer, Field
from .models import Account, AccTypeEnum, AccountFactory


# !!!! TODO -> Make AccTypeField behave as we want it to behave.
class AccTypeField(Field):
    """ Transforms a string into a value in AccTypeEnum """

    # !!!! TODO -> Really make this method
    def to_internal_value(self, data):
        return AccTypeEnum.BRANCH

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

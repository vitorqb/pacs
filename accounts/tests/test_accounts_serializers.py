from rest_framework.exceptions import ValidationError

from common.test import PacsTestCase
from accounts.models import AccTypeEnum, Account, get_root_acc
from accounts.serializers import AccTypeField, AccountSerializer
from accounts.management.commands.populate_accounts import account_populator, account_type_populator
from .factories import AccountTestFactory


class TestAccTypeField(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.field = AccTypeField()

    def test_to_internal_value(self):
        for acc_type in AccTypeEnum:
            with self.subTest(acc_type):
                value = acc_type.value.lower()
                parsed = self.field.to_internal_value(value)
                assert parsed == acc_type

    def test_to_internal_value_wrong_raises_validation_error(self):
        unkown_type = "alo213h21"
        assert unkown_type not in set(x.value for x in AccTypeEnum)
        with self.assertRaises(ValidationError):
            self.field.to_internal_value(unkown_type)

    def test_to_representation(self):
        for acc_type in AccTypeEnum:
            with self.subTest(acc_type=acc_type):
                assert self.field.to_representation(acc_type) == acc_type.value


class TestAccountSerializer(PacsTestCase):

    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()
        self.data = {
            "name": "Acc",
            "acc_type": AccTypeEnum.LEAF.value,
            "parent": get_root_acc().pk
        }

    def create(self):
        """ Creates using the serializer and self.data """
        ser = AccountSerializer(data=self.data)
        ser.is_valid(True)
        return ser.save()

    def test_create_account(self):
        acc = self.create()
        assert acc.get_name() == self.data['name']
        assert acc in Account.objects.all()

    def test_create_acc_repeated_name_raises_validation_error(self):
        acc = AccountTestFactory()
        self.data['name'] = acc.get_name()
        with self.assertRaises(ValidationError) as e:
            self.create()
        assert 'name' in e.exception.detail

    def test_create_acc_pk_is_ignored_if_parsed(self):
        self.data['pk'] = 123
        acc = self.create()
        assert acc.pk != self.data['pk']

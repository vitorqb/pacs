from rest_framework.exceptions import ValidationError

from common.test import PacsTestCase
from accounts.models import AccTypeEnum
from accounts.serializers import AccTypeField


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

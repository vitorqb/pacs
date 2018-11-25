
from rest_framework.exceptions import ValidationError

from common.test import PacsTestCase
from currencies.serializers import CurrencySerializer
from currencies.models import Currency


class TestCurrencySerializer_create(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.data = {"name": "Yen"}

    def create(self):
        ser = CurrencySerializer(data=self.data)
        ser.is_valid(True)
        return ser.save()

    def test_base(self):
        cur = self.create()
        assert cur in Currency.objects.all()
        assert cur.name == self.data['name']

    def test_imutable_read_only(self):
        self.data['imutable'] = True
        cur = self.create()
        assert cur.imutable is False

    def test_repeated_name_raises_err(self):
        self.create()
        with self.assertRaises(ValidationError) as e:
            self.create()
        assert 'name' in e.exception.detail

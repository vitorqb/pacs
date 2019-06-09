from unittest import TestCase
from decimal import Decimal

from rest_framework.serializers import ValidationError

from common.serializers import new_price_field


class TestPriceField(TestCase):

    def test_to_internal_value(self):
        new_price_field().to_internal_value(10) == Decimal(10)

    def test_to_representation(self):
        new_price_field().to_representation(Decimal(10)) == '10.00000'

    def test_min_value(self):
        with self.assertRaises(ValidationError) as e:
            new_price_field().run_validation(-1)
        assert 'positive' in str(e.exception)

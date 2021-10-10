from unittest import TestCase
from decimal import Decimal
from rest_framework.serializers import ValidationError

import common.serializers as sut
import pytest


class TestPriceField(TestCase):

    def test_to_internal_value(self):
        sut.new_price_field().to_internal_value(10) == Decimal(10)

    def test_to_representation(self):
        sut.new_price_field().to_representation(Decimal(10)) == '10.00000'

    def test_min_value(self):
        with self.assertRaises(ValidationError) as e:
            sut.new_price_field().run_validation(-1)
        assert 'positive' in str(e.exception)


class CurrencyCodesFieldTest(TestCase):

    def test_valid(self):
        valid_value = "A,BBB,CCCCC"
        field = sut.CurrencyCodesField()
        result = field.run_validation(valid_value)
        assert result == ["A", "BBB", "CCCCC"]

    def test_invalid(self):
        invalid_value = 1
        field = sut.CurrencyCodesField()
        with pytest.raises(ValidationError):
            field.run_validation(invalid_value)

from unittest import TestCase
import exchange_rate_fetcher.serializers as sut
import pytest
from rest_framework.validators import ValidationError


class newStringDateFieldTest(TestCase):

    def test_valid(self):
        valid_date = "2019-01-01"
        field = sut._new_string_date_field()
        field.run_validation(valid_date)

    def test_invalid(self):
        invalid_date = "2019-1-01"
        field = sut._new_string_date_field()
        with pytest.raises(ValidationError):
            field.run_validation(invalid_date)


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

from unittest import TestCase
import exchange_rate_fetcher.serializers as sut
import pytest
from rest_framework.validators import ValidationError


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

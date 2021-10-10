import pytest
from unittest import TestCase
import common.models as sut
from rest_framework.validators import ValidationError


class newStringDateFieldTest(TestCase):

    def test_valid(self):
        valid_date = "2019-01-01"
        field = sut.new_string_date_field()
        field.run_validation(valid_date)

    def test_invalid(self):
        invalid_date = "2019-1-01"
        field = sut.new_string_date_field()
        with pytest.raises(ValidationError):
            field.run_validation(invalid_date)

from unittest import TestCase
from datetime import date
import common.utils as sut


class TestDateToStr(TestCase):

    def test_base(self):
        assert sut.date_to_str(date(2011, 12, 12)) == "2011-12-12"
        assert sut.date_to_str(date(1993, 2, 2)) == "1993-02-02"


class TestDateRange(TestCase):

    def test_one_long(self):
        assert sut.date_range(date(2020, 1, 1), date(2020, 1, 1)) == [date(2020, 1, 1)]

    def test_three_long(self):
        result = sut.date_range(date(2020, 1, 1), date(2020, 1, 3))
        expected = [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)]
        assert result == expected

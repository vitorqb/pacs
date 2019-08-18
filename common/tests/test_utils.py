from unittest import TestCase
from datetime import date
from common.utils import date_to_str


class TestDateToStr(TestCase):

    def test_base(self):
        assert date_to_str(date(2011, 12, 12)) == "2011-12-12"
        assert date_to_str(date(1993, 2, 2)) == "1993-02-02"

from decimal import Decimal
from unittest import TestCase

from common.utils import decimals_equal


class TestCommon(TestCase):
    def test_decimals_equal_equal(self):
        one = Decimal("123.4567")
        two = one + Decimal("0.0001")
        assert decimals_equal(one, two) is True

    def test_decimals_equal_not_equal_limit(self):
        one = Decimal("123.005")
        two = one + Decimal("0.001")
        assert decimals_equal(one, two) is False

    def test_decimals_equal_not_equal(self):
        one = Decimal("1.128")
        two = one - Decimal("0.003")
        assert decimals_equal(one, two) is False

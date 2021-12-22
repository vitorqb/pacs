from unittest import TestCase

import featuretoggles.utils as sut


class ParseTogglesTest(TestCase):
    def test_empty(self):
        assert sut.parse_toggles("") == {}

    def test_three_long(self):
        assert sut.parse_toggles(" foo,!bar ,baz") == {"foo": True, "bar": False, "baz": True}


class SerializeTogglesTest(TestCase):
    def test_empty(self):
        assert sut.serialize_toggles({}) == ""

    def test_three_long(self):
        assert sut.serialize_toggles({"foo": True, "bar": False, "baz": True}) == "foo,!bar,baz"

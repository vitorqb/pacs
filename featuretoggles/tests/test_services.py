from unittest import TestCase
from unittest.mock import Mock

from django.test import override_settings

import featuretoggles.services as sut


class FeatureToggleServiceTest(TestCase):

    default_toggles = {"foo": False, "bar": False, "zzz": True}

    @override_settings(FEATURE_TOGGLES="")
    def test_dont_fail_with_empty(self):
        featureToggleService = sut.FeatureToggleService({}, Mock(META={}))
        assert featureToggleService.is_active("foo") is None

    @override_settings(FEATURE_TOGGLES="foo,!bar")
    def test_loads_default_toggles_from_settings(self):
        featureToggleService = sut.FeatureToggleService(self.default_toggles, Mock(META={}))
        assert featureToggleService.is_active("foo") is True
        assert featureToggleService.is_active("bar") is False
        assert featureToggleService.is_active("baz") is None
        assert featureToggleService.is_active("zzz") is True

    @override_settings(FEATURE_TOGGLES="foo,!bar", FEATURE_TOGGLE_REQUEST_HEADER="FF")
    def test_loads_toggles_from_request(self):
        request = Mock()
        request.META = {"FF": "!foo,bar"}
        featureToggleService = sut.FeatureToggleService(self.default_toggles, request)
        assert featureToggleService.is_active("foo") is False
        assert featureToggleService.is_active("bar") is True
        assert featureToggleService.is_active("baz") is None
        assert featureToggleService.is_active("zzz") is True

from unittest import TestCase
from unittest.mock import Mock
import featuretoggles.services as sut
from django.test import override_settings


class FeatureToggleServiceTest(TestCase):

    @override_settings(FEATURE_TOGGLES='')
    def test_dont_fail_with_empty(self):
        featureToggleService = sut.FeatureToggleService(request=Mock(META={}))
        assert featureToggleService.is_active("foo") is None

    @override_settings(FEATURE_TOGGLES='foo,!bar')
    def test_loads_default_toggles_from_settings(self):
        featureToggleService = sut.FeatureToggleService(request=Mock(META={}))
        assert featureToggleService.is_active("foo") is True
        assert featureToggleService.is_active("bar") is False
        assert featureToggleService.is_active("baz") is None

    @override_settings(FEATURE_TOGGLES='foo,!bar', FEATURE_TOGGLE_REQUEST_HEADER='FF')
    def test_loads_toggles_from_request(self):
        request = Mock()
        request.META = {"FF": "!foo,bar"}
        featureToggleService = sut.FeatureToggleService(request=request)
        assert featureToggleService.is_active("foo") is False
        assert featureToggleService.is_active("bar") is True
        assert featureToggleService.is_active("baz") is None

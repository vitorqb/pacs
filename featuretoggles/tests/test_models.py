from django.test import override_settings

import featuretoggles.models as sut
from common.testutils import PacsTestCase


class FeatureToggleQuerySetTest(PacsTestCase):
    @override_settings(CACHES={"default": {"BACKEND": "featuretoggles.utils.FakeCache"}})
    def test_reads_from_cache(self):
        assert sut.FeatureToggle.objects.read_feature_toggles() == {"foo": True, "bar": False}

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
    )
    def test_reads_from_db(self):
        sut.FeatureToggle(name="foo", is_active=False).save()
        sut.FeatureToggle(name="bar", is_active=True).save()
        assert sut.FeatureToggle.objects.read_feature_toggles() == {"foo": False, "bar": True}
        sut.FeatureToggle.objects.all().delete()

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import featuretoggles.models as models
import pytest
from common.test import TestRequests


@pytest.mark.functional
class FunctionalTests(StaticLiveServerTestCase):

    def test_get_feature_toggles(self):
        models.FeatureToggle.objects.create(name="foo", is_active=True).save()
        models.FeatureToggle.objects.create(name="bar", is_active=False).save()
        result = TestRequests(self.live_server_url).get("/featuretoggles")
        assert result.status_code == 200
        assert result.json() == {"foo": True, "bar": False}

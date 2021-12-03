from common.testutils import PacsTestCase
import featuretoggles.models as models


class GetFeatureTogglesTest(PacsTestCase):

    def test_returns_200_with_feature_toggles(self):
        models.FeatureToggle.objects.create(name="foo", is_active=True)
        result = self.client.get("/featuretoggles")
        assert result.status_code == 200
        assert result.json() == {"foo": True}

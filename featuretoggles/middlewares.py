import featuretoggles.models as models
import featuretoggles.services as services


class FeatureToggleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        default_toggles = models.FeatureToggle.objects.read_feature_toggles()
        featureToggleService = services.FeatureToggleService(default_toggles, request)
        services.set_instance(featureToggleService)
        return self.get_response(request)

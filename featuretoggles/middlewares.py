import featuretoggles.services as services


class FeatureToggleMiddleware():

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        featureToggleService = services.FeatureToggleService(request)
        services.set_instance(featureToggleService)
        return self.get_response(request)

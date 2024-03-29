import copy

from django.conf import settings

import featuretoggles.models
import featuretoggles.utils


class FeatureToggleService:
    def __init__(self, default_toggles, request):
        request_toggles_str = request.META.get(settings.FEATURE_TOGGLE_REQUEST_HEADER, "")
        settings_toggles_str = settings.FEATURE_TOGGLES
        self._features = {
            **default_toggles,
            **featuretoggles.utils.parse_toggles(settings_toggles_str),
            **featuretoggles.utils.parse_toggles(request_toggles_str),
        }

    def is_active(self, feature_name):
        return self._features.get(feature_name, None)

    def get_dict(self):
        return copy.deepcopy(self._features)


instance = None


def set_instance(x):
    global instance
    instance = x


def get_instance():
    if instance is None:
        raise RuntimeError("FeatureToggleService was not properly initialized.")
    return instance

import django.db.models as models
from django.core.cache import cache

import featuretoggles.utils

CACHE_KEY = "featuretoggles"
CACHE_TIMEOUT = 120


class FeatureToggleQuerySet(models.QuerySet):
    def read_feature_toggles(self):
        from_cache = cache.get(CACHE_KEY)
        if from_cache:
            return featuretoggles.utils.parse_toggles(from_cache)
        from_db = {x.name: x.is_active for x in self.all()}
        cache.set(CACHE_KEY, featuretoggles.utils.serialize_toggles(from_db), CACHE_TIMEOUT)
        return from_db


class FeatureToggle(models.Model):
    name = models.TextField(unique=True, blank=False, null=False)
    is_active = models.BooleanField(blank=False, null=False)

    objects = FeatureToggleQuerySet.as_manager()

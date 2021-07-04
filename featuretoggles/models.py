import django.db.models as models
from django.core.cache import cache


class FeatureToggleQuerySet(models.QuerySet):

    def read_feature_toggles():
        feature_toggles_str = cache.get("feature_toggles")


class FeatureToggle(models.Model):
    name = models.TextField(unique=True, blank=False, null=False)
    is_active = models.BooleanField(blank=False, null=False)

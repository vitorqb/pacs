from django.core.exceptions import PermissionDenied


class MissingApiKey(PermissionDenied):
    pass


class InvalidApiKey(PermissionDenied):
    pass


class InvalidRole(PermissionDenied):
    pass

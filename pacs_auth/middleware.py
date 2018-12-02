from django.conf import settings

from django.core.exceptions import PermissionDenied


class PacsAuthMiddleware:
    """ An authentication scheme that simply looks at
    Authentication header and checks if it equals to
    'Token {settings.ADMIN_TOKEN} """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        exp_authorization = f"Token {settings.ADMIN_TOKEN}"
        if request.META.get('HTTP_AUTHORIZATION') == exp_authorization:
            return self.get_response(request)
        raise PermissionDenied()

from django.core.exceptions import PermissionDenied
from pacs_auth.services import AuthorizerFactory
import logging


logger = logging.getLogger(__name__)


class PacsAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        authorizer = AuthorizerFactory(request)()
        authorizer.run_validation()
        return self.get_response(request)


class PacsDummyAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get("HTTP_PACS_TEST_AUTH") == "1":
            return self.get_response(request)
        raise PermissionDenied()

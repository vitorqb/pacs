import logging

from django.core.exceptions import PermissionDenied

from pacs_auth.services import AuthorizerFactory

logger = logging.getLogger(__name__)


class PacsAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        authorizer = AuthorizerFactory(request)()
        authorizer.run_validation()
        return self.get_response(request)

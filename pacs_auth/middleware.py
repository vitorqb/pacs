from django.conf import settings
from django.core.exceptions import PermissionDenied
from pacs_auth.models import Token
import re
import logging


logger = logging.getLogger(__name__)


class PacsAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in settings.PACS_AUTH_ALLOWED_URLS:
            logger.info(f"Request to {request.path} does not required auth")
            return self.get_response(request)

        authorization = request.META.get('HTTP_AUTHORIZATION')
        if not authorization:
            logger.info("Permission denied due to missing token")
            raise PermissionDenied()

        token_match = re.compile("(Token|TOKEN)[ ]+(.*)").match(authorization)
        if not token_match:
            logger.info("Permission denied due to token incorrect format")
            raise PermissionDenied()

        token_value = token_match.groups()[1]
        if not Token.objects.is_valid_token_value(token_value):
            logger.info("Permission denied due to invalid token")
            raise PermissionDenied()

        return self.get_response(request)


class PacsDummyAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get("HTTP_PACS_TEST_AUTH") == "1":
            return self.get_response(request)
        raise PermissionDenied()

import logging
import re

import attr
from django.conf import settings
from django.core.exceptions import PermissionDenied

import pacs_auth.exceptions as exceptions
from pacs_auth.models import ApiKey, Token

logger = logging.getLogger(__name__)


#
# Token Validators
#
class ITokenValidator:
    def is_valid(self, token_value):
        raise NotImplementedError()


@attr.s(frozen=True)
class TokenValidator(ITokenValidator):

    token_manager = attr.ib(factory=(lambda: Token.objects))

    def is_valid(self, token_value):
        return self.token_manager.is_valid_token_value(token_value)


@attr.s(frozen=True)
class SingleStaticTokenValidator(ITokenValidator):

    valid_token = attr.ib(default="valid_token")

    def is_valid(self, token_value):
        return token_value == self.valid_token


def get_token_validator():
    if getattr(settings, "TOKEN_VALIDATOR_CLASS", None) == "SingleStaticTokenValidator":
        return SingleStaticTokenValidator()
    return TokenValidator()


#
# Authorizers
#
class IAuthorizer:
    def run_validation(self):
        raise NotImplementedError()


@attr.s(frozen=True)
class AllAllowedAuthorizer(IAuthorizer):

    request = attr.ib()

    def run_validation(self):
        pass


@attr.s(frozen=True)
class TokenAuthorizer(IAuthorizer):

    request = attr.ib()
    token_validator = attr.ib(factory=get_token_validator)

    def run_validation(self):
        authorization = self.get_authorization(self.request)
        if not authorization:
            logger.info("Permission denied due to missing token")
            raise PermissionDenied()

        token_match = re.compile("(Token|TOKEN)[ ]+(.*)").match(authorization)
        if not token_match:
            logger.info("Permission denied due to token incorrect format")
            raise PermissionDenied()

        token_value = token_match.groups()[1]
        if not self.token_validator.is_valid(token_value):
            logger.info("Permission denied due to invalid token")
            raise PermissionDenied()

    @classmethod
    def get_authorization(cls, request):
        return request.META.get("HTTP_AUTHORIZATION")


@attr.s(frozen=True)
class ApiKeyAuthorizer(IAuthorizer):

    request = attr.ib()
    api_key_manager = attr.ib(factory=(lambda: ApiKey.objects))
    roles_auth_rules = attr.ib(factory=(lambda: settings.PACS_AUTH_ROLE_AUTH_RULES))

    def run_validation(self):
        api_key_value = self.request.META.get("HTTP_X_PACS_API_KEY")

        if not api_key_value:
            logger.info("Missing api_key in request")
            raise exceptions.MissingApiKey()

        api_key = self.api_key_manager.get_valid_api_key(api_key_value)
        if not api_key:
            logger.info("No api_key found for given value")
            raise exceptions.InvalidApiKey()

        needed_role_name = next(
            x["role"] for x in self.roles_auth_rules if x["path"] == self.request.path
        )
        if needed_role_name not in (x.role_name for x in api_key.roles.all()):
            logger.info(f"Role {needed_role_name} not in api_key roles {api_key.roles.all()}")
            raise exceptions.InvalidRole()


@attr.s(frozen=True)
class AuthorizerFactory:

    request = attr.ib()
    allowed_urls = attr.ib(factory=(lambda: settings.PACS_AUTH_ALLOWED_URLS))
    roles_auth_rules = attr.ib(factory=(lambda: settings.PACS_AUTH_ROLE_AUTH_RULES))

    def __call__(self):
        if self.request.path in self.allowed_urls:
            return AllAllowedAuthorizer(self.request)
        if TokenAuthorizer.get_authorization(self.request) is not None:
            return TokenAuthorizer(self.request)
        if self.request.path in (x["path"] for x in self.roles_auth_rules):
            return ApiKeyAuthorizer(self.request)
        return TokenAuthorizer(self.request)

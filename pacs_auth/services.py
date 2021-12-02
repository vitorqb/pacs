import attr
from django.conf import settings
from django.core.exceptions import PermissionDenied
from pacs_auth.models import Token
import re
import logging


logger = logging.getLogger(__name__)


#
# Token Validators
#
class ITokenValidator():

    def is_valid(self, token_value):
        raise NotImplementedError()


@attr.s(frozen=True)
class TokenValidator(ITokenValidator):

    token_manager = attr.ib(factory=(lambda: Token.objects))

    def is_valid(self, token_value):
        return self.token_manager.is_valid_token_value(token_value)


@attr.s(frozen=True)
class SingleStaticTokenValidator(ITokenValidator):

    valid_token = attr.ib(default='valid_token')

    def is_valid(self, token_value):
        return token_value == self.valid_token


def get_token_validator():
    if getattr(settings, 'TOKEN_VALIDATOR_CLASS', None) == 'SingleStaticTokenValidator':
        return SingleStaticTokenValidator()
    return TokenValidator()


#
# Authorizers
#
class IAuthorizer():
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
        authorization = self.request.META.get('HTTP_AUTHORIZATION')
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


@attr.s(frozen=True)
class ApiKeyAuthorizer(IAuthorizer):

    request = attr.ib()

    def run_validation(self):
        # TODO
        return True


@attr.s(frozen=True)
class AuthorizerFactory():

    request = attr.ib()
    allowed_urls = attr.ib(factory=(lambda: settings.PACS_AUTH_ALLOWED_URLS))
    roles_auth_rules = attr.ib(factory=(lambda: settings.PACS_AUTH_ROLE_AUTH_RULES))

    def __call__(self):
        if self.request.path in self.allowed_urls:
            return AllAllowedAuthorizer(self.request)
        if self.request.path in (x['path'] for x in self.roles_auth_rules):
            return ApiKeyAuthorizer(self.request)
        return TokenAuthorizer(self.request)

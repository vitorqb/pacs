from common.test import PacsTestCase
from rest_framework.test import APIRequestFactory
from django.core.exceptions import PermissionDenied
import pacs_auth.services as sut
import pytest
import attr


@attr.s()
class TokenValidatorMock():

    single_valid_token = 'a_valid_token'

    def is_valid(self, token_value):
        return token_value == self.single_valid_token


class TestTokenAuthorizer(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.request_factory = APIRequestFactory()

    def test_fails_if_not_authorization_header(self):
        request = self.request_factory.get('/foo')
        authorizer = sut.TokenAuthorizer(request)
        with pytest.raises(PermissionDenied):
            authorizer.run_validation()

    def test_fails_if_token_in_incorrect_format(self):
        request = self.request_factory.get('/foo', HTTP_AUTHORIZATION='INVALID')
        authorizer = sut.TokenAuthorizer(request)
        with pytest.raises(PermissionDenied):
            authorizer.run_validation()

    def test_fails_if_token_not_valid(self):
        request = self.request_factory.get('/foo', HTTP_AUTHORIZATION='TOKEN an_invalid_token')
        authorizer = sut.TokenAuthorizer(request, token_validator=TokenValidatorMock())
        with pytest.raises(PermissionDenied):
            authorizer.run_validation()

    def test_allows_if_valid_token(self):
        request = self.request_factory.get('/foo', HTTP_AUTHORIZATION='TOKEN a_valid_token')
        authorizer = sut.TokenAuthorizer(request, token_validator=TokenValidatorMock())
        authorizer.run_validation()


class TestAuthorizerFactory(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.request_factory = APIRequestFactory()

    def new_authorizer_factory(self, request, *, allowed_urls=None, roles_auth_rules=None):
        allowed_urls = allowed_urls or []
        roles_auth_rules = roles_auth_rules or []
        return sut.AuthorizerFactory(
            request,
            allowed_urls=allowed_urls,
            roles_auth_rules=roles_auth_rules
        )

    def test_returns_all_allowed_if_inside_allowed_urls(self):
        request = self.request_factory.get("/bar")
        allowed_urls = ["/foo", "/bar"]
        authorizer_factory = self.new_authorizer_factory(request, allowed_urls=allowed_urls)
        authorizer = authorizer_factory()
        assert isinstance(authorizer, sut.AllAllowedAuthorizer)

    def test_returns_api_key_authorizer_if_role_is_set(self):
        request = self.request_factory.get("/bar")
        roles_auth_rules = [
            {'path': '/bar', 'role': 'TEST_ROLE'}
        ]
        authorizer_factory = self.new_authorizer_factory(request, roles_auth_rules=roles_auth_rules)
        authorizer = authorizer_factory()
        assert isinstance(authorizer, sut.ApiKeyAuthorizer)

    def test_returns_token_authorizer_if_not_an_allowed_url(self):
        request = self.request_factory.get("/bar")
        allowed_urls = ["/foo"]
        authorizer_factory = self.new_authorizer_factory(request, allowed_urls=allowed_urls)
        authorizer = authorizer_factory()
        assert isinstance(authorizer, sut.TokenAuthorizer)

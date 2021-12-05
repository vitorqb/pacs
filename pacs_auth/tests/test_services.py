from common.testutils import PacsTestCase
from rest_framework.test import APIRequestFactory
from django.core.exceptions import PermissionDenied
import pacs_auth.services as sut
import pacs_auth.exceptions as exceptions
import pacs_auth.models as models
import pytest
import attr


@attr.s()
class TokenValidatorMock():

    single_valid_token = 'a_valid_token'

    def is_valid(self, token_value):
        return token_value == self.single_valid_token


@attr.s()
class ApiKeyManagerMock():

    api_key_value = "a_valid_api_key"
    api_key_role_name = "a_role"

    def get_valid_api_key(self, value):
        if not value == self.api_key_value:
            return
        api_key = models.ApiKey(value=self.api_key_value)
        api_key.save()
        role = models.ApiKeyRole(api_key=api_key, role_name=self.api_key_role_name)
        role.save()
        api_key.roles.add(role)
        return api_key


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

    def test_returns_token_authorizer_if_a_token_is_present_even_if_api_key(self):
        request = self.request_factory.get("/bar", HTTP_AUTHORIZATION='TOKEN a_valid_token')
        roles_auth_rules = [{'path': '/bar', 'role': 'TEST_ROLE'}]
        authorizer_factory = self.new_authorizer_factory(request, roles_auth_rules=roles_auth_rules)
        authorizer = authorizer_factory()
        assert isinstance(authorizer, sut.TokenAuthorizer)


class TestApiKeyAuthorizer(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.request_factory = APIRequestFactory()

    def mk_request(self, api_key="123"):
        kwargs = {}
        if api_key:
            kwargs["HTTP_X_PACS_API_KEY"] = api_key
        return self.request_factory.get("/auth/test", **kwargs)

    def test_fails_because_missing_api_key(self):
        request = self.mk_request(api_key=None)
        authorizer = sut.ApiKeyAuthorizer(request)
        with pytest.raises(exceptions.MissingApiKey):
            authorizer.run_validation()

    def test_fails_because_api_key_not_found(self):
        request = self.mk_request()
        api_key_manager = ApiKeyManagerMock()
        authorizer = sut.ApiKeyAuthorizer(request, api_key_manager=api_key_manager)
        with pytest.raises(exceptions.InvalidApiKey):
            authorizer.run_validation()

    def test_fails_because_wrong_role_for_call(self):
        request = self.mk_request(api_key="a_valid_api_key")
        api_key_manager = ApiKeyManagerMock()
        roles_auth_rules = [{"path": "/auth/test", "role": "another_role"}]
        authorizer = sut.ApiKeyAuthorizer(
            request,
            api_key_manager=api_key_manager,
            roles_auth_rules=roles_auth_rules
        )
        with pytest.raises(exceptions.InvalidRole):
            authorizer.run_validation()

    def test_success(self):
        request = self.mk_request(api_key="a_valid_api_key")
        api_key_manager = ApiKeyManagerMock()
        roles_auth_rules = [
            {"path": "/auth/test", "role": api_key_manager.api_key_role_name}
        ]
        authorizer = sut.ApiKeyAuthorizer(
            request,
            api_key_manager=api_key_manager,
            roles_auth_rules=roles_auth_rules
        )
        authorizer.run_validation()

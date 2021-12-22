from datetime import timedelta
from unittest import mock

import attr
from rest_framework.test import APIClient, override_settings

import common.utils
from common.testutils import PacsTestCase
from pacs_auth.models import ApiKey, ApiKeyFactory, Token, TokenFactory


def old_date_fn():
    return common.utils.utcdatetime(1999, 1, 1)


short_duration = timedelta(seconds=1)
ADMIN_TOKEN = "secret_token"


@attr.s()
class MockApiKeyFactory:
    def __call__(self, roles):
        return ApiKey(value="FOO")


class TestRecoverToken(PacsTestCase):
    def store_token_in_session(self, token_value):
        session = self.client.session
        session["token_value"] = token_value
        session.save()

    def test_recovers_token_from_session(self):
        token = TokenFactory()()
        self.store_token_in_session(token.value)
        response = self.client.get("/auth/token")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token_value"], token.value)

    def test_bad_request_if_no_token(self):
        token_factory = TokenFactory()
        token_factory()
        response = self.client.get("/auth/token")
        self.assertEqual(response.status_code, 400)

    def test_bad_request_if_expired_token(self):
        token_factory = TokenFactory(now_fn=old_date_fn, duration=short_duration)
        token = token_factory()
        self.store_token_in_session(token.value)
        response = self.client.get("/auth/token")
        self.assertEqual(response.status_code, 400)

    def test_bad_request_if_invalid_token_value(self):
        token_factory = TokenFactory(now_fn=old_date_fn, duration=short_duration)
        token = token_factory()
        self.store_token_in_session(token.value + "F")
        response = self.client.get("/auth/token")
        self.assertEqual(response.status_code, 400)


@override_settings(ADMIN_TOKEN=ADMIN_TOKEN)
class TestCreateToken(PacsTestCase):
    def get_client(self):
        return APIClient(HTTP_PACS_TEST_AUTH="1")

    def get_data(self):
        return {"admin_token": ADMIN_TOKEN}

    def test_creates_token_in_the_db(self):
        self.assertEqual(Token.objects.all().count(), 0)
        response = self.get_client().post("/auth/token", data=self.get_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.all().count(), 1)
        self.assertEqual(Token.objects.all().first().value, response.json()["token_value"])

    def test_sets_cookie_with_token(self):
        client = self.get_client()
        response = client.post("/auth/token", data=self.get_data())
        self.assertEqual(client.session["token_value"], response.json()["token_value"])

    def test_fails_for_missing_admin_token(self):
        self.assertEqual(Token.objects.all().count(), 0)
        response = self.get_client().post("/auth/token")
        self.assertEqual(Token.objects.all().count(), 0)
        self.assertEqual(response.status_code, 400)

    def test_fails_for_wrong_admin_token(self):
        self.assertEqual(Token.objects.all().count(), 0)
        response = self.get_client().post("/auth/token", {"admin_token": "123"})
        self.assertEqual(Token.objects.all().count(), 0)
        self.assertEqual(response.status_code, 400)


@override_settings(ADMIN_TOKEN=ADMIN_TOKEN)
class TestCreateApiKey(PacsTestCase):
    def get_data(self, **kwargs):
        return {
            **{
                "roles": ["TEST"],
                "admin_token": ADMIN_TOKEN,
            },
            **kwargs,
        }

    def test_creates_api_key_using_factory(self):
        with mock.patch("pacs_auth.views.ApiKeyFactory", MockApiKeyFactory):
            response = self.client.post("/auth/api_key", data=self.get_data())
        assert response.status_code == 200
        assert response.json()["api_key"] == "FOO"

    def test_fails_if_wrong_admin_token(self):
        response = self.client.post("/auth/api_key", data=self.get_data(admin_token="INVALID"))
        assert response.status_code == 400

    def test_fails_if_missing_roles(self):
        response = self.client.post("/auth/api_key", data=self.get_data(roles=[]))
        assert response.status_code == 400

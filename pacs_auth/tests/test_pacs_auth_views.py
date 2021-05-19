from common.test import PacsTestCase
from pacs_auth.models import TokenFactory, Token
from datetime import timedelta
import common.utils
from rest_framework.test import override_settings, APIClient


def old_date_fn():
    return common.utils.utcdatetime(1999, 1, 1)


short_duration = timedelta(seconds=1)
ADMIN_TOKEN = "secret_token"


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

    def get_authorized_client(self):
        return APIClient(HTTP_AUTHORIZATION=f"Token {ADMIN_TOKEN}")

    def get_unauthorized_client(self):
        return APIClient(HTTP_AUTHORIZATION=f"Token wrong_token")

    def test_creates_token_in_the_db(self):
        self.assertEqual(Token.objects.all().count(), 0)
        response = self.get_authorized_client().post("/auth/token")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.all().count(), 1)
        self.assertEqual(Token.objects.all().first().value, response.json()["token_value"])

    def test_sets_cookie_with_token(self):
        client = self.get_authorized_client()
        response = client.post("/auth/token")
        self.assertEqual(client.session["token_value"], response.json()["token_value"])

    def test_fails_for_unauthorized_client(self):
        self.assertEqual(Token.objects.all().count(), 0)
        response = self.get_unauthorized_client().post("/auth/token")
        self.assertEqual(Token.objects.all().count(), 0)
        self.assertEqual(response.status_code, 403)
from common.test import PacsTestCase
import pacs_auth.views as sut
from pacs_auth.models import TokenFactory
from datetime import timedelta
import common.utils


def old_date_fn():
    return common.utils.utcdatetime(1999, 1, 1)


short_duration = timedelta(seconds=1)


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

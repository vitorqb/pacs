from common.test import PacsTestCase
import pacs_auth.models as sut
from common import utils
from datetime import timedelta


def now_fn():
    return utils.utcdatetime(2020, 1, 1)


def old_date_fn():
    return utils.utcdatetime(1990, 1, 1)


def gen_token_fn():
    return "1234567890"


class TestTokenFactory(PacsTestCase):

    def test_create_token(self):
        factory = sut.TokenFactory(now_fn, gen_token_fn)
        token = factory()
        self.assertEqual(token.value, "1234567890")
        self.assertEqual(token.valid_until, utils.utcdatetime(2020, 1, 2))


class TestToken(PacsTestCase):

    def test_is_valid_token_value_true(self):
        factory = sut.TokenFactory()
        token = factory()
        self.assertTrue(sut.Token.objects.is_valid_token_value(token.value))

    def test_is_valid_token_value_missing_token(self):
        factory = sut.TokenFactory()
        token = factory()
        self.assertFalse(sut.Token.objects.is_valid_token_value(token.value + "F"))

    def test_is_valid_token_value_expired(self):
        factory = sut.TokenFactory(now_fn=old_date_fn, duration=timedelta(days=1))
        token = factory()
        self.assertFalse(sut.Token.objects.is_valid_token_value(token.value))


class TestApiKeyQuerySet(PacsTestCase):

    def test_finds_and_returns(self):
        api_key = sut.ApiKey.objects.create(value="123")
        found = sut.ApiKey.objects.get_valid_api_key("123")
        assert api_key == found

    def test_does_not_finds_and_returns_none(self):
        found = sut.ApiKey.objects.get_valid_api_key("123")
        assert found is None

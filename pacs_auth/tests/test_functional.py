import pytest
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from common.test import TestRequests


@pytest.mark.functional
class PacsAuthFunctionalTests(StaticLiveServerTestCase):

    @override_settings(ADMIN_TOKEN="123")
    def test_fails_to_create_if_missing_admin_token(self):
        api_key_request = TestRequests(self.live_server_url)
        api_key_result = api_key_request.post(
            "/auth/api_key",
            json={"roles": ["API_KEY_TEST"], "admin_token": "456"}
        )
        assert api_key_result.status_code == 400

    @override_settings(ADMIN_TOKEN="123")
    def test_creates_and_uses_api_key_with_permission_set(self):
        api_key_request = TestRequests(self.live_server_url)
        api_key_result = api_key_request.post(
            "/auth/api_key",
            json={"roles": ["API_KEY_TEST"], "admin_token": "123"}
        )
        api_key = api_key_result.json()["api_key"]

        auth_headers = {"x-pacs-api-key": api_key}
        test_request = TestRequests(self.live_server_url)
        test_request_result = test_request.get("/auth/test", extra_headers=auth_headers)
        assert test_request_result.status_code == 200

    @override_settings(ADMIN_TOKEN="123")
    def test_calling_endpoint_with_missing_permission_returns_forbidden(self):
        auth_headers = {"x-pacs-api-key": "not-an-api-key"}
        test_request = TestRequests(self.live_server_url)
        test_request_result = test_request.get("/auth/test", extra_headers=auth_headers)
        assert test_request_result.status_code == 403

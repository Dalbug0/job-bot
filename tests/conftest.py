# tests/conftest.py

import pytest


@pytest.fixture
def mock_httpx_response():
    """Фикстура для мока httpx.Response"""
    class MockResponse:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json_data = json_data or {}
            self.text = text

        def json(self):
            return self._json_data

    return MockResponse

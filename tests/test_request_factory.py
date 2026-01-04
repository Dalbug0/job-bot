# tests/test_request_factory.py

from unittest.mock import AsyncMock, patch

import pytest

from api_facade import GetRequest, PostRequest, PutRequest, RequestFactory


@pytest.mark.unit
class TestRequestFactory:
    """Тесты для RequestFactory"""

    def test_create_get_request_basic(self):
        """Тест создания базового GET запроса"""
        url = "https://api.example.com/test"
        request = RequestFactory.create_get_request(url)

        assert isinstance(request, GetRequest)
        assert request.url == url
        assert request.headers == {}
        assert request.params is None
        assert request.timeout is None

    def test_create_get_request_with_params(self):
        """Тест создания GET запроса с параметрами"""
        url = "https://api.example.com/test"
        headers = {"Authorization": "Bearer token"}
        params = {"page": 1, "limit": 10}
        timeout = 30.0

        request = RequestFactory.create_get_request(
            url, headers, params, timeout
        )

        assert isinstance(request, GetRequest)
        assert request.url == url
        assert request.headers == headers
        assert request.params == params
        assert request.timeout == timeout

    def test_create_post_request_basic(self):
        """Тест создания базового POST запроса"""
        url = "https://api.example.com/test"
        data = {"key": "value"}

        request = RequestFactory.create_post_request(url, data)

        assert isinstance(request, PostRequest)
        assert request.url == url
        assert request.data == data
        assert request.headers == {}
        assert request.timeout is None

    def test_create_post_request_with_headers_timeout(self):
        """Тест создания POST запроса с заголовками и таймаутом"""
        url = "https://api.example.com/test"
        data = {"key": "value"}
        headers = {"Content-Type": "application/json"}
        timeout = 60.0

        request = RequestFactory.create_post_request(
            url, data, headers, timeout
        )

        assert isinstance(request, PostRequest)
        assert request.url == url
        assert request.data == data
        assert request.headers == headers
        assert request.timeout == timeout

    def test_create_put_request_basic(self):
        """Тест создания базового PUT запроса"""
        url = "https://api.example.com/test"
        data = {"key": "value"}

        request = RequestFactory.create_put_request(url, data)

        assert isinstance(request, PutRequest)
        assert request.url == url
        assert request.data == data
        assert request.headers == {}
        assert request.timeout is None

    def test_create_put_request_full(self):
        """Тест создания полного PUT запроса"""
        url = "https://api.example.com/test"
        data = {"key": "value"}
        headers = {"Authorization": "Bearer token"}
        timeout = 45.0

        request = RequestFactory.create_put_request(
            url, data, headers, timeout
        )

        assert isinstance(request, PutRequest)
        assert request.url == url
        assert request.data == data
        assert request.headers == headers
        assert request.timeout == timeout

    @pytest.mark.asyncio
    async def test_get_request_execute(self, mock_httpx_response):
        """Тест выполнения GET запроса"""
        url = "https://api.example.com/test"
        headers = {"Authorization": "Bearer token"}
        params = {"page": 1}

        request = RequestFactory.create_get_request(url, headers, params)

        with patch("httpx.AsyncClient") as mock_client_class:
            from unittest.mock import AsyncMock

            mock_client = mock_client_class.return_value
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_httpx_response)

            response = await request.execute()

            mock_client.get.assert_called_once_with(
                url, headers=headers, params=params
            )
            assert response == mock_httpx_response

    @pytest.mark.asyncio
    async def test_post_request_execute(self, mock_httpx_response):
        """Тест выполнения POST запроса"""
        url = "https://api.example.com/test"
        data = {"key": "value"}
        headers = {"Content-Type": "application/json"}
        timeout = 30.0

        request = RequestFactory.create_post_request(
            url, data, headers, timeout
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            from unittest.mock import AsyncMock

            mock_client = mock_client_class.return_value
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_httpx_response)

            response = await request.execute()

            mock_client.post.assert_called_once_with(
                url, json=data, headers=headers
            )
            assert response == mock_httpx_response

    @pytest.mark.asyncio
    async def test_put_request_execute(self, mock_httpx_response):
        """Тест выполнения PUT запроса"""
        url = "https://api.example.com/test"
        data = {"key": "value"}
        headers = {"Authorization": "Bearer token"}

        request = RequestFactory.create_put_request(url, data, headers)

        with patch("httpx.AsyncClient") as mock_client_class:
            from unittest.mock import AsyncMock

            mock_client = mock_client_class.return_value
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_httpx_response)

            response = await request.execute()

            mock_client.put.assert_called_once_with(
                url, json=data, headers=headers
            )
            assert response == mock_httpx_response

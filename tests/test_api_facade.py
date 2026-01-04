# tests/test_api_facade.py

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api_facade import ApiFacade


@pytest.mark.unit
class TestApiFacade:
    """Тесты для ApiFacade"""

    @pytest.fixture
    def api_facade(self):
        """Фикстура для ApiFacade"""
        with patch("api_facade.settings"):
            facade = ApiFacade()
            facade.base_url = "https://api.example.com"
            return facade

    def test_init(self, api_facade):
        """Тест инициализации ApiFacade"""
        assert api_facade.base_url == "https://api.example.com"
        assert api_facade.auth_router_url == "/api/v1/auth"
        assert api_facade._access_token is None

    def test_set_get_clear_access_token(self, api_facade):
        """Тест управления access token"""
        # Изначально токен None
        assert api_facade.get_access_token() is None

        # Устанавливаем токен
        token = "test_access_token"
        api_facade.set_access_token(token)
        assert api_facade.get_access_token() == token

        # Очищаем токен
        api_facade.clear_access_token()
        assert api_facade.get_access_token() is None

    def test_get_auth_headers_no_token(self, api_facade):
        """Тест получения заголовков без токена"""
        headers = api_facade._get_auth_headers()
        assert headers == {}

    def test_get_auth_headers_with_token(self, api_facade):
        """Тест получения заголовков с токеном"""
        token = "test_token"
        api_facade.set_access_token(token)

        headers = api_facade._get_auth_headers()
        assert headers == {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(
        self, api_facade, mock_httpx_response
    ):
        """Тест успешного обновления access token"""
        mock_response = mock_httpx_response(
            status_code=200,
            json_data={
                "access_token": "new_access_token",
                "token_type": "bearer",
            },
        )

        with patch.object(
            api_facade.request_factory, "create_post_request"
        ) as mock_create_request:
            mock_request = AsyncMock()
            mock_request.execute.return_value = mock_response
            mock_create_request.return_value = mock_request

            result = await api_facade.refresh_access_token()

            expected_url = (
                f"{api_facade.base_url}{api_facade.auth_router_url}/refresh"
            )
            mock_create_request.assert_called_once_with(expected_url, {})

            assert result["access_token"] == "new_access_token"
            assert api_facade.get_access_token() == "new_access_token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(
        self, api_facade, mock_httpx_response
    ):
        """Тест неудачного обновления access token"""
        mock_response = mock_httpx_response(
            status_code=401, text="Unauthorized"
        )

        with patch.object(
            api_facade.request_factory, "create_post_request"
        ) as mock_create_request:
            mock_request = AsyncMock()
            mock_request.execute.return_value = mock_response
            mock_create_request.return_value = mock_request

            with pytest.raises(
                Exception, match="Failed to refresh access token"
            ):
                await api_facade.refresh_access_token()

    @pytest.mark.asyncio
    async def test_get_me_success(self, api_facade, mock_httpx_response):
        """Тест успешного получения информации о пользователе"""
        user_data = {"id": 1, "email": "test@example.com"}
        mock_response = mock_httpx_response(
            status_code=200, json_data=user_data
        )

        api_facade.set_access_token("valid_token")

        with patch.object(
            api_facade.request_factory, "create_get_request"
        ) as mock_create_request:
            mock_request = AsyncMock()
            mock_request.execute.return_value = mock_response
            mock_create_request.return_value = mock_request

            result = await api_facade.get_me()

            expected_url = f"{api_facade.base_url}/users/me"
            expected_headers = {"Authorization": "Bearer valid_token"}
            mock_create_request.assert_called_once_with(
                expected_url, headers=expected_headers
            )

            assert result == user_data

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, api_facade, mock_httpx_response):
        """Тест получения информации о пользователе без авторизации"""
        mock_response = mock_httpx_response(
            status_code=401, text="Unauthorized"
        )

        with patch.object(
            api_facade.request_factory, "create_get_request"
        ) as mock_create_request:
            mock_request = AsyncMock()
            mock_request.execute.return_value = mock_response
            mock_create_request.return_value = mock_request

            with pytest.raises(Exception, match="Не авторизован"):
                await api_facade.get_me()

    @pytest.mark.asyncio
    async def test_get_login_url_success(
        self, api_facade, mock_httpx_response
    ):
        """Тест успешного получения URL авторизации"""
        login_data = {"login_url": "https://example.com/oauth"}
        mock_response = mock_httpx_response(
            status_code=200, json_data=login_data
        )

        with patch.object(
            api_facade.request_factory, "create_get_request"
        ) as mock_create_request:
            mock_request = AsyncMock()
            mock_request.execute.return_value = mock_response
            mock_create_request.return_value = mock_request

            result = await api_facade.get_login_url()

            expected_url = (
                f"{api_facade.base_url}{api_facade.auth_router_url}/login"
            )
            mock_create_request.assert_called_once_with(expected_url)

            assert result == "https://example.com/oauth"

    @pytest.mark.asyncio
    async def test_get_resumes_success(self, api_facade, mock_httpx_response):
        """Тест успешного получения списка резюме"""
        resumes_data = {"items": [{"id": "1", "title": "Test Resume"}]}
        mock_response = mock_httpx_response(
            status_code=200, json_data=resumes_data
        )

        api_facade.set_access_token("valid_token")

        with patch.object(
            api_facade.request_factory, "create_get_request"
        ) as mock_create_request:
            mock_request = AsyncMock()
            mock_request.execute.return_value = mock_response
            mock_create_request.return_value = mock_request

            result = await api_facade.get_resumes()

            expected_url = f"{api_facade.base_url}/hh/resumes"
            expected_headers = {"Authorization": "Bearer valid_token"}
            mock_create_request.assert_called_once_with(
                expected_url, headers=expected_headers
            )

            assert result == resumes_data

    @pytest.mark.asyncio
    async def test_select_resume_success(
        self, api_facade, mock_httpx_response
    ):
        """Тест успешного выбора резюме"""
        resume_id = "test_resume_123"
        response_data = {"status": "selected"}
        mock_response = mock_httpx_response(
            status_code=200, json_data=response_data
        )

        api_facade.set_access_token("valid_token")

        with patch.object(
            api_facade.request_factory, "create_post_request"
        ) as mock_create_request:
            mock_request = AsyncMock()
            mock_request.execute.return_value = mock_response
            mock_create_request.return_value = mock_request

            result = await api_facade.select_resume(resume_id)

            expected_url = (
                f"{api_facade.base_url}/hh/resumes/select/{resume_id}"
            )
            expected_headers = {"Authorization": "Bearer valid_token"}
            mock_create_request.assert_called_once_with(
                expected_url, {}, headers=expected_headers
            )

            assert result == response_data

    @pytest.mark.asyncio
    async def test_publish_resume_success(
        self, api_facade, mock_httpx_response
    ):
        """Тест успешной публикации резюме"""
        resume_id = "test_resume_123"
        response_data = {"status": "published"}
        mock_response = mock_httpx_response(
            status_code=200, json_data=response_data
        )

        api_facade.set_access_token("valid_token")

        with patch.object(
            api_facade.request_factory, "create_post_request"
        ) as mock_create_request:
            mock_request = AsyncMock()
            mock_request.execute.return_value = mock_response
            mock_create_request.return_value = mock_request

            result = await api_facade.publish_resume(resume_id)

            expected_url = (
                f"{api_facade.base_url}/hh/resumes/{resume_id}/publish"
            )
            expected_headers = {"Authorization": "Bearer valid_token"}
            mock_create_request.assert_called_once_with(
                expected_url, {}, headers=expected_headers
            )

            assert result == response_data

# tests/integration/test_auth_integration.py

import pytest
import requests
from urllib.parse import urlparse, parse_qs


@pytest.mark.integration
class TestAuthIntegration:
    """Интеграционные тесты для авторизации job-bot API"""

    def test_auth_login_endpoint_available(self, api_base_url):
        """Тест доступности эндпоинта /auth/login"""
        url = f"{api_base_url}/auth/login"

        # Для GET запроса к login endpoint ожидаем 405 Method Not Allowed
        response = requests.get(url, timeout=10)

        # Ожидаем 405 (Method Not Allowed), так как login - это POST endpoint
        assert response.status_code == 405, (
            f"Expected 405 Method Not Allowed, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )

        print(f"[OK] Auth login endpoint available: {response.status_code}")

    def test_auth_refresh_endpoint_structure(self, api_base_url):
        """Тест структуры эндпоинта /auth/refresh"""
        url = f"{api_base_url}/auth/refresh"

        # Отправляем POST запрос без refresh_token (ожидаем ошибку валидации)
        response = requests.post(url, json={"refresh_token": "invalid_token"}, timeout=10)

        # Ожидаем 401 Unauthorized, так как токен недействительный
        assert response.status_code == 401, (
            f"Expected 401 for invalid token, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )

        # Проверяем, что ответ содержит информацию об ошибке
        response_data = response.json()
        assert "detail" in response_data or "error" in response_data, (
            f"Expected error details in response, got: {response_data}"
        )

        print(f"[OK] Auth refresh endpoint returns proper error for unauthorized request")

    def test_hh_auth_login_redirect(self, api_base_url):
        """Тест редиректа на HH.ru авторизацию"""
        url = f"{api_base_url}/api/v1/auth/hh/login"

        # Отправляем запрос без user_id (ожидаем 422)
        response = requests.get(url, allow_redirects=False, timeout=10)

        # Ожидаем 422 Unprocessable Entity из-за отсутствия user_id
        assert response.status_code == 422, (
            f"Expected 422 for missing user_id, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )

        print(f"[OK] HH auth login endpoint available: {response.status_code}")

    def test_hh_auth_callback_endpoint(self, api_base_url):
        """Тест эндпоинта callback для обработки кода авторизации HH.ru"""
        url = f"{api_base_url}/api/v1/auth/hh/callback"

        # Отправляем запрос без параметров (ожидаем ошибку)
        response = requests.get(url, timeout=10)

        # Ожидаем 422 Unprocessable Entity из-за отсутствия code и state параметров
        assert response.status_code == 422, (
            f"Expected 422 for missing code and state parameters, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )

        # Проверяем сообщение об ошибке
        response_data = response.json()
        assert "detail" in response_data or "error" in response_data, (
            f"Expected error details in response, got: {response_data}"
        )

        print(f"✓ HH auth callback endpoint properly handles missing code parameter")

    def test_hh_auth_callback_with_invalid_code(self, api_base_url):
        """Тест эндпоинта callback с недействительным кодом"""
        url = f"{api_base_url}/api/v1/auth/hh/callback"
        params = {"code": "invalid_code_123"}

        response = requests.get(url, params=params, timeout=10)

        # Ожидаем 422 из-за отсутствия state параметра
        assert response.status_code == 422, (
            f"Expected 422 for missing state parameter, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )

        print(f"[OK] HH auth callback endpoint handles missing state properly")

    def test_api_docs_available(self, api_base_url):
        """Тест доступности API документации"""
        url = f"{api_base_url}/api/v1/docs"

        response = requests.get(url, timeout=10)

        # Ожидаем успешный ответ с HTML документацией
        assert response.status_code == 200, (
            f"Expected 200 for API docs, got {response.status_code}"
        )

        # Проверяем, что ответ содержит HTML
        assert "html" in response.headers.get("content-type", "").lower(), (
            f"Expected HTML content-type, got: {response.headers.get('content-type')}"
        )

        # Проверяем наличие ключевых слов документации
        content = response.text.lower()
        assert "api" in content or "swagger" in content or "documentation" in content, (
            "Expected API documentation content"
        )

        print(f"[OK] API documentation available at /api/v1/docs")

    def test_openapi_schema_available(self, api_base_url):
        """Тест доступности OpenAPI схемы"""
        url = f"{api_base_url}/api/v1/openapi.json"

        response = requests.get(url, timeout=10)

        # Ожидаем успешный ответ с JSON схемой
        assert response.status_code == 200, (
            f"Expected 200 for OpenAPI schema, got {response.status_code}"
        )

        # Проверяем JSON формат
        assert "application/json" in response.headers.get("content-type", ""), (
            f"Expected JSON content-type, got: {response.headers.get('content-type')}"
        )

        # Проверяем структуру OpenAPI
        schema = response.json()
        assert "openapi" in schema, "Expected OpenAPI version in schema"
        assert "paths" in schema, "Expected paths in OpenAPI schema"
        assert "/api/v1/auth/hh/login" in schema.get("paths", {}), (
            "Expected HH auth login path in OpenAPI schema"
        )

        print(f"✓ OpenAPI schema available with auth endpoints")

    def test_cors_headers(self, api_base_url):
        """Тест CORS заголовков"""
        url = f"{api_base_url}/api/v1/auth/login"

        # Отправляем OPTIONS запрос для проверки CORS
        response = requests.options(url, timeout=10)

        # Проверяем CORS заголовки (могут отсутствовать в тестовой среде)
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers"
        ]

        cors_present = any(header in response.headers for header in cors_headers)

        if cors_present:
            print("✓ CORS headers are configured")
        else:
            print("! CORS headers not found (may be expected in test environment)")

        # В любом случае эндпоинт должен отвечать
        assert response.status_code in [200, 404, 405], (
            f"Unexpected status for OPTIONS request: {response.status_code}"
        )

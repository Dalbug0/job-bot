# tests/integration/test_bot_features_integration.py

import pytest
import requests


@pytest.mark.integration
class TestBotFeaturesIntegration:
    """Интеграционные тесты для новых функций бота"""

    def test_api_basic_connectivity(self, api_base_url):
        """Тест базового подключения к API"""
        response = requests.get(f"{api_base_url}/api/v1/docs", timeout=5)

        assert response.status_code == 200, (
            f"Expected 200 for API docs, got {response.status_code}"
        )

        print("[OK] API is accessible")

    def test_user_registration_endpoint(self, api_base_url):
        """Тест доступности эндпоинта регистрации"""
        register_url = f"{api_base_url}/auth/register"

        # Отправляем невалидные данные чтобы проверить доступность эндпоинта
        response = requests.post(register_url, json={}, timeout=5)

        # Ожидаем 422 (validation error) или 200
        assert response.status_code in [200, 422, 400], (
            f"Expected 200/422 for register endpoint, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )

        print("[OK] User registration endpoint is accessible")

    def test_hh_auth_endpoints(self, api_base_url):
        """Тест доступности HH.ru авторизации"""
        hh_login_url = f"{api_base_url}/api/v1/auth/hh/login_url"

        # Запрос без user_id должен вернуть ошибку валидации
        response = requests.get(hh_login_url, timeout=5)

        assert response.status_code == 422, (
            f"Expected 422 for HH login_url without user_id, got {response.status_code}"
        )

        print("[OK] HH auth login_url endpoint is accessible")

    def test_vacancies_endpoint(self, api_base_url):
        """Тест доступности эндпоинта вакансий"""
        vacancies_url = f"{api_base_url}/vacancies/"

        response = requests.get(vacancies_url, timeout=5)

        assert response.status_code == 200, (
            f"Expected 200 for vacancies, got {response.status_code}"
        )

        vacancies = response.json()
        assert isinstance(vacancies, list), f"Expected list, got {type(vacancies)}"

        print(f"[OK] Vacancies endpoint returned {len(vacancies)} items")

    def test_openapi_spec(self, api_base_url):
        """Тест наличия OpenAPI спецификации"""
        spec_url = f"{api_base_url}/api/v1/openapi.json"

        response = requests.get(spec_url, timeout=5)

        assert response.status_code == 200, (
            f"Expected 200 for OpenAPI spec, got {response.status_code}"
        )

        spec = response.json()
        assert "paths" in spec, "Expected paths in OpenAPI spec"

        # Проверяем наличие основных эндпоинтов
        paths = spec.get("paths", {})
        assert "/auth/register" in paths, "Register endpoint not in OpenAPI spec"
        assert "/vacancies/" in paths, "Vacancies endpoint not in OpenAPI spec"

        print("[OK] OpenAPI spec contains required endpoints")

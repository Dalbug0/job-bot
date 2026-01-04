import secrets
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import httpx

from config import settings


class BaseRequest(ABC):
    """Базовый класс для HTTP запросов"""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout

    @abstractmethod
    async def execute(self) -> httpx.Response:
        """Выполнить HTTP запрос"""
        pass


class GetRequest(BaseRequest):
    """Класс для GET запросов"""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ):
        super().__init__(url, headers, timeout)
        self.params = params

    async def execute(self) -> httpx.Response:
        client_kwargs = {}
        if self.timeout is not None:
            client_kwargs["timeout"] = self.timeout
        async with httpx.AsyncClient(**client_kwargs) as client:
            return await client.get(
                self.url, headers=self.headers, params=self.params
            )


class PostRequest(BaseRequest):
    """Класс для POST запросов"""

    def __init__(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ):
        super().__init__(url, headers, timeout)
        self.data = data

    async def execute(self) -> httpx.Response:
        client_kwargs = {}
        if self.timeout is not None:
            client_kwargs["timeout"] = self.timeout
        async with httpx.AsyncClient(**client_kwargs) as client:
            return await client.post(
                self.url, json=self.data, headers=self.headers
            )


class PutRequest(BaseRequest):
    """Класс для PUT запросов"""

    def __init__(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ):
        super().__init__(url, headers, timeout)
        self.data = data

    async def execute(self) -> httpx.Response:
        client_kwargs = {}
        if self.timeout is not None:
            client_kwargs["timeout"] = self.timeout
        async with httpx.AsyncClient(**client_kwargs) as client:
            return await client.put(
                self.url, json=self.data, headers=self.headers
            )


class RequestFactory:
    """Фабрика для создания объектов запросов"""

    @staticmethod
    def create_get_request(
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> GetRequest:
        return GetRequest(url, headers, params, timeout)

    @staticmethod
    def create_post_request(
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> PostRequest:
        return PostRequest(url, data, headers, timeout)

    @staticmethod
    def create_put_request(
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> PutRequest:
        return PutRequest(url, data, headers, timeout)


class ApiFacade:
    """Фасад для работы с API"""

    def __init__(self):
        self.base_url = settings.API_URL
        self.request_factory = RequestFactory()
        self.auth_router_url = "/auth"
        self._access_token: Optional[str] = None
        self._internal_user_id: Optional[int] = None

    def set_access_token(self, token: str) -> None:
        """Установить access token для авторизации"""
        self._access_token = token

    def get_access_token(self) -> Optional[str]:
        """Получить текущий access token"""
        return self._access_token

    def clear_access_token(self) -> None:
        """Очистить access token"""
        self._access_token = None

    def set_internal_user_id(self, user_id: int) -> None:
        """Установить internal user ID для Telegram пользователей"""
        self._internal_user_id = user_id

    def get_internal_user_id(self) -> Optional[int]:
        """Получить internal user ID"""
        return self._internal_user_id

    def clear_internal_user_id(self) -> None:
        """Очистить internal user ID"""
        self._internal_user_id = None

    def _get_auth_headers(self) -> Dict[str, str]:
        """Получить заголовки с авторизацией"""
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        elif self._internal_user_id:
            # Для Telegram пользователей используем X-User-ID
            headers["X-User-ID"] = str(self._internal_user_id)
        return headers

    async def refresh_access_token(self) -> Dict[str, Any]:
        """Обновить access token через refresh token (хранится в API)"""
        url = f"{self.base_url}{self.auth_router_url}/refresh"
        request = self.request_factory.create_post_request(url, {})
        response = await request.execute()

        if response.status_code == 200:
            data = response.json()
            self._access_token = data.get("access_token")
            return data
        else:
            raise Exception(
                f"Failed to refresh access token: {response.status_code}, {response.text}"
            )

    async def get_login_url(self) -> str:
        """Получить URL для авторизации"""
        url = f"{self.base_url}{self.auth_router_url}/login"
        request = self.request_factory.create_get_request(url)
        response = await request.execute()

        if response.status_code == 200:
            data = response.json()
            return data.get("login_url", "")
        else:
            raise Exception(
                f"Failed to get login URL: {response.status_code}, {response.text}"
            )

    async def get_me(self) -> Dict[str, Any]:
        """Получить информацию о текущем пользователе"""
        url = f"{self.base_url}/users/me"
        headers = self._get_auth_headers()
        request = self.request_factory.create_get_request(url, headers=headers)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        elif response.status_code in (401, 403):
            # Попытка обновить токен
            try:
                await self.refresh_access_token()
                # Повторный запрос с новым токеном
                headers = self._get_auth_headers()
                request = self.request_factory.create_get_request(
                    url, headers=headers
                )
                response = await request.execute()
                if response.status_code == 200:
                    return response.json()
            except Exception:
                pass
            raise Exception("Не авторизован. Подключите аккаунт через /login")
        else:
            raise Exception(
                f"Failed to get user info: {response.status_code}, {response.text}"
            )

    async def get_resumes(self) -> Dict[str, Any]:
        """Получить список резюме"""
        url = f"{self.base_url}/api/v1/auth/hh/resumes"
        headers = self._get_auth_headers()
        request = self.request_factory.create_get_request(url, headers=headers)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        elif response.status_code in (401, 403):
            raise Exception("Не авторизован. Подключите аккаунт через /login")
        else:
            raise Exception(
                f"Failed to get resumes: {response.status_code}, {response.text}"
            )

    async def get_vacancies(self) -> list:
        """Получить список вакансий"""
        url = f"{self.base_url}/vacancies/"
        request = self.request_factory.create_get_request(url)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to get vacancies: {response.status_code}, {response.text}"
            )

    async def add_vacancy(
        self, title: str, company: str, location: str, description: str
    ) -> Dict[str, Any]:
        """Добавить новую вакансию"""
        url = f"{self.base_url}/vacancies/"
        data = {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
        }
        request = self.request_factory.create_post_request(url, data)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to add vacancy: {response.status_code}, {response.text}"
            )

    async def update_vacancy(
        self,
        vacancy_id: str,
        title: str,
        company: str,
        location: str,
        description: str,
    ) -> Dict[str, Any]:
        """Обновить вакансию"""
        url = f"{self.base_url}/vacancies/{vacancy_id}/"
        data = {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
        }
        request = self.request_factory.create_put_request(url, data)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to update vacancy: {response.status_code}, {response.text}"
            )

    async def select_resume(self, resume_id: str) -> Dict[str, Any]:
        """Выбрать активное резюме"""
        url = f"{self.base_url}/api/v1/auth/hh/resumes/select/{resume_id}"
        headers = self._get_auth_headers()
        request = self.request_factory.create_post_request(
            url, {}, headers=headers
        )
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        elif response.status_code in (401, 403):
            raise Exception("Не авторизован. Подключите аккаунт через /login")
        else:
            raise Exception(
                f"Failed to select resume: {response.status_code}, {response.text}"
            )

    async def publish_resume(self, resume_id: str) -> Dict[str, Any]:
        """Опубликовать/поднять резюме"""
        url = f"{self.base_url}/api/v1/auth/hh/resumes/{resume_id}/publish"
        headers = self._get_auth_headers()
        request = self.request_factory.create_post_request(
            url, {}, headers=headers
        )
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        elif response.status_code in (401, 403):
            raise Exception("Не авторизован. Подключите аккаунт через /login")
        else:
            raise Exception(
                f"Failed to publish resume: {response.status_code}, {response.text}"
            )

    async def register_user(
        self, username: str, email: str, telegram_id: int
    ) -> int:
        """Зарегистрировать нового пользователя через email"""
        password = secrets.token_urlsafe(16)  # Генерируем случайный пароль

        url = f"{self.base_url}/auth/register"
        data = {"username": username, "email": email, "password": password}
        request = self.request_factory.create_post_request(url, data)
        response = await request.execute()

        if response.status_code == 200:
            result = response.json()
            return result.get("user_id")
        else:
            raise Exception(
                f"Failed to register user: {response.status_code}, {response.text}"
            )

    async def register_telegram_user(
        self,
        telegram_id: int,
        telegram_username: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> dict:
        """Зарегистрировать нового пользователя через Telegram"""
        url = f"{self.base_url}/auth/register/telegram"
        data = {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "first_name": first_name,
            "last_name": last_name,
        }
        request = self.request_factory.create_post_request(url, data)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to register telegram user: {response.status_code}, {response.text}"
            )

    async def get_telegram_user_info(self, telegram_id: int) -> dict:
        """Получить информацию о Telegram пользователе из API"""
        url = f"{self.base_url}/users/telegram/{telegram_id}"
        request = self.request_factory.create_get_request(url)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            # Пользователь не найден - это нормально, вернем None или пустой dict
            return {}
        else:
            raise Exception(
                f"Failed to get telegram user info: {response.status_code}, {response.text}"
            )

    async def get_hh_login_url(self, user_id: int) -> str:
        """Получить URL для авторизации HH.ru"""
        url = f"{self.base_url}/api/v1/auth/hh/login_url?user_id={user_id}"
        request = self.request_factory.create_get_request(url)
        response = await request.execute()

        if response.status_code == 200:
            # API возвращает URL авторизации HH.ru
            return response.json().get("login_url", "")
        else:
            raise Exception(
                f"Failed to get HH login URL: {response.status_code}, {response.text}"
            )

    async def get_hh_token_status(self, user_id: int) -> Dict[str, Any]:
        """Получить статус HH токена пользователя"""
        url = f"{self.base_url}/api/v1/auth/hh/token/{user_id}"
        request = self.request_factory.create_get_request(url)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to get HH token status: {response.status_code}, {response.text}"
            )

    async def search_vacancies(
        self,
        company: Optional[str] = None,
        location: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> list:
        """Поиск вакансий по параметрам"""
        url = f"{self.base_url}/vacancies/"
        params = {}
        if company:
            params["company"] = company
        if location:
            params["location"] = location
        params["skip"] = skip
        params["limit"] = limit

        request = self.request_factory.create_get_request(url, params=params)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to search vacancies: {response.status_code}, {response.text}"
            )

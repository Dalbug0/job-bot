from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx

from config import settings


class BaseRequest(ABC):
    """Базовый класс для HTTP запросов"""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}

    @abstractmethod
    async def execute(self) -> httpx.Response:
        """Выполнить HTTP запрос"""
        pass


class GetRequest(BaseRequest):
    """Класс для GET запросов"""

    async def execute(self) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.get(self.url, headers=self.headers)


class PostRequest(BaseRequest):
    """Класс для POST запросов"""

    def __init__(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(url, headers)
        self.data = data

    async def execute(self) -> httpx.Response:
        async with httpx.AsyncClient() as client:
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
    ):
        super().__init__(url, headers)
        self.data = data

    async def execute(self) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.put(
                self.url, json=self.data, headers=self.headers
            )


class RequestFactory:
    """Фабрика для создания объектов запросов"""

    @staticmethod
    def create_get_request(
        url: str, headers: Optional[Dict[str, str]] = None
    ) -> GetRequest:
        return GetRequest(url, headers)

    @staticmethod
    def create_post_request(
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> PostRequest:
        return PostRequest(url, data, headers)

    @staticmethod
    def create_put_request(
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> PutRequest:
        return PutRequest(url, data, headers)


class ApiFacade:
    """Фасад для работы с API"""

    def __init__(self):
        self.base_url = settings.API_URL
        self.request_factory = RequestFactory()
        self.hh_router_URL = "/api/v1/auth"

    async def get_resumes(self) -> Dict[str, Any]:
        """Получить список резюме"""
        url = f"{self.base_url}/hh/resumes"
        request = self.request_factory.create_get_request(url)
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
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
        url = f"{self.base_url}/hh/resumes/select/{resume_id}"
        request = self.request_factory.create_post_request(url, {})
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to select resume: {response.status_code}, {response.text}"
            )

    async def publish_resume(self, resume_id: str) -> Dict[str, Any]:
        """Опубликовать/поднять резюме"""
        url = f"{self.base_url}/hh/resumes/{resume_id}/publish"
        request = self.request_factory.create_post_request(url, {})
        response = await request.execute()

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to publish resume: {response.status_code}, {response.text}"
            )

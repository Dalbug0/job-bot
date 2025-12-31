# tests/integration/conftest.py

import subprocess
import time
import requests
import pytest
import os
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def docker_compose():
    """Фикстура для запуска и остановки docker-compose окружения"""

    # Путь к docker-compose.yml в корне проекта (родительская директория job-bot)
    project_root = Path(__file__).parent.parent.parent.parent
    docker_compose_file = project_root / "docker-compose.yml"

    if not docker_compose_file.exists():
        pytest.skip(f"docker-compose.yml not found at {docker_compose_file}")

    # Останавливаем и удаляем предыдущие контейнеры
    try:
        subprocess.run(
            ["docker-compose", "-f", str(docker_compose_file), "down", "-v"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError:
        pass  # Игнорируем ошибки при остановке

    # Запускаем сервисы
    try:
        subprocess.run(
            ["docker-compose", "-f", str(docker_compose_file), "up", "-d"],
            check=True,
            capture_output=True,
            text=True,
            cwd=project_root
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to start docker-compose: {e.stderr}")

    yield

    # Останавливаем сервисы после тестов
    try:
        subprocess.run(
            ["docker-compose", "-f", str(docker_compose_file), "down", "-v"],
            check=True,
            capture_output=True,
            text=True,
            cwd=project_root
        )
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to stop docker-compose: {e.stderr}")


@pytest.fixture(scope="session")
def api_base_url(docker_compose):
    """Фикстура для получения базового URL API после ожидания готовности"""

    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    max_attempts = 30  # 30 попыток по 5 секунд = 2.5 минуты
    attempt = 0

    while attempt < max_attempts:
        try:
            # Проверяем готовность API через health check или простой GET запрос
            response = requests.get(f"{base_url}/docs", timeout=5)
            if response.status_code == 200:
                print(f"API is ready at {base_url}")
                return base_url
        except requests.RequestException:
            pass

        attempt += 1
        print(f"Waiting for API... attempt {attempt}/{max_attempts}")
        time.sleep(5)

    # Если API не поднялся, проверяем логи контейнера
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        result = subprocess.run(
            ["docker-compose", "-f", str(project_root / "docker-compose.yml"), "logs", "api"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        logs = result.stdout + result.stderr
        print(f"API container logs:\n{logs}")
    except Exception as e:
        print(f"Failed to get container logs: {e}")

    pytest.fail(
        f"API at {base_url} is not ready after {max_attempts} attempts. "
        "Check docker-compose logs and container status."
    )

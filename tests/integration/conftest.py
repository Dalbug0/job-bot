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

    # Путь к docker-compose.test.yml в корне проекта
    project_root = Path(__file__).parent.parent.parent.parent
    docker_compose_file = project_root / "docker-compose.test.yml"

    if not docker_compose_file.exists():
        pytest.skip(f"docker-compose.test.yml not found at {docker_compose_file}")

    # Проверяем наличие необходимых .env файлов
    env_files = [project_root / ".env.dev", project_root / ".env.hh.dev"]
    missing_env_files = [f for f in env_files if not f.exists()]

    if missing_env_files:
        pytest.skip(f"Missing environment files: {[str(f) for f in missing_env_files]}")

    # Останавливаем и удаляем предыдущие контейнеры
    try:
        subprocess.run(
            ["docker-compose", "-f", str(docker_compose_file), "down", "-v", "--remove-orphans"],
            check=True,
            capture_output=True,
            text=True,
            cwd=project_root
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
def api_base_url():
    """Фикстура для получения базового URL API после ожидания готовности"""

    # Используем тестовый порт без /api/v1 в конце
    base_url = os.getenv("API_BASE_URL", "http://localhost:8001")  # 8001 - тестовый порт
    max_attempts = 60  # 60 попыток по 5 секунд = 5 минут
    attempt = 0

    while attempt < max_attempts:
        try:
            # Проверяем готовность API
            response = requests.get(f"{base_url}/api/v1/docs", timeout=10)
            if response.status_code == 200:
                print(f"API is ready at {base_url}")
                return base_url
        except requests.RequestException as e:
            if attempt % 10 == 0:  # Логируем каждые 10 попыток
                print(f"Waiting for API at {base_url}... attempt {attempt}/{max_attempts} ({e})")

        attempt += 1
        time.sleep(5)

    # Если API не поднялся, показываем логи контейнеров
    _show_container_logs()

    pytest.fail(
        f"API at {base_url} is not ready after {max_attempts} attempts. "
        "Check docker-compose.test.yml logs and container status."
    )


def _show_container_logs():
    """Показать логи контейнеров для отладки"""
    project_root = Path(__file__).parent.parent.parent.parent
    compose_file = project_root / "docker-compose.test.yml"

    if not compose_file.exists():
        print(f"docker-compose.test.yml not found at {compose_file}")
        return

    try:
        # Пытаемся получить логи всех контейнеров
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "logs"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30
        )

        if result.returncode == 0:
            logs = result.stdout + result.stderr
            print(f"\n=== Container logs ===")
            # Показываем последние 100 строк логов
            lines = logs.split('\n')[-100:]
            print('\n'.join(lines))
        else:
            print(f"Failed to get container logs: {result.stderr}")

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print(f"Could not retrieve container logs: {e}")

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
def api_base_url():
    """Фикстура для получения базового URL API после ожидания готовности

    Работает как с локальным запуском docker-compose, так и с централизованным
    тестовым окружением через run_integration_tests.py
    """

    base_url = os.getenv("API_BASE_URL", "http://localhost:8001")  # 8001 - тестовый порт
    max_attempts = 30  # 30 попыток по 5 секунд = 2.5 минуты
    attempt = 0

    while attempt < max_attempts:
        try:
            # Проверяем готовность API через health check или простой GET запрос
            response = requests.get(f"{base_url}/api/v1/docs", timeout=5)
            if response.status_code == 200:
                print(f"API is ready at {base_url}")
                return base_url
        except requests.RequestException:
            pass

        attempt += 1
        print(f"Waiting for API... attempt {attempt}/{max_attempts}")
        time.sleep(5)

    # Если API не поднялся, пытаемся получить логи из разных возможных источников
    _show_container_logs(base_url)

    pytest.fail(
        f"API at {base_url} is not ready after {max_attempts} attempts. "
        "Check docker-compose logs and container status."
    )


def _show_container_logs(base_url):
    """Показать логи контейнеров для отладки"""
    # Пытаемся получить логи из разных возможных docker-compose файлов
    possible_compose_files = [
        "docker-compose.test.yml",  # Централизованное тестовое окружение
        "docker-compose.yml",       # Основное окружение
    ]

    for compose_file in possible_compose_files:
        compose_path = Path(__file__).parent.parent.parent.parent / compose_file
        if compose_path.exists():
            try:
                # Пытаемся получить логи API контейнера
                for container_name in ["job_platform_test_api", "job_api"]:
                    result = subprocess.run(
                        ["docker-compose", "-f", str(compose_path), "logs", container_name],
                        capture_output=True,
                        text=True,
                        cwd=compose_path.parent,
                        timeout=30
                    )
                    if result.returncode == 0 and (result.stdout or result.stderr):
                        logs = result.stdout + result.stderr
                        print(f"\n=== Container logs ({container_name}) ===")
                        # Показываем последние 50 строк логов
                        lines = logs.split('\n')[-50:]
                        print('\n'.join(lines))
                        return
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                continue

    print(f"Could not retrieve container logs for API at {base_url}")

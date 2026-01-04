#!/usr/bin/env python3
"""
Скрипт для запуска интеграционных тестов job-bot.

Этот скрипт:
1. Проверяет наличие Docker и docker-compose
2. Запускает интеграционные тесты
3. Показывает понятные сообщения об ошибках
"""

import os
import subprocess
import sys
from pathlib import Path


def check_docker():
    """Проверяет наличие Docker и docker-compose"""
    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✓ Docker: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Docker не установлен или не запущен")
        return False

    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✓ Docker Compose: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Docker Compose не установлен")
        return False

    return True


def check_env_files():
    """Проверяет наличие необходимых файлов окружения"""
    project_root = Path(__file__).parent.parent
    env_files = [project_root / ".env.dev", project_root / ".env.hh.dev"]

    missing_files = []
    for env_file in env_files:
        if not env_file.exists():
            missing_files.append(env_file.name)

    if missing_files:
        print(f"✗ Отсутствуют файлы окружения: {', '.join(missing_files)}")
        print(
            "  Создайте их на основе примеров или получите от администратора проекта"
        )
        return False

    print("✓ Файлы окружения найдены")
    return True


def run_tests():
    """Запускает интеграционные тесты"""
    print("\n🚀 Запуск интеграционных тестов...")

    # Переходим в директорию проекта
    os.chdir(Path(__file__).parent)

    # Запускаем тесты
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/",
                "-v",
                "--tb=short",
            ],
            check=True,
        )

        print("\n✅ Все интеграционные тесты пройдены!")
        return True

    except subprocess.CalledProcessError as e:
        print(
            f"\n❌ Интеграционные тесты провалились (код выхода: {e.returncode})"
        )
        print("Подробности выше. Проверьте логи Docker контейнеров:")
        print("  docker-compose logs api")
        return False


def main():
    """Основная функция"""
    print("🧪 Проверка интеграционных тестов job-bot")
    print("=" * 50)

    # Проверяем зависимости
    if not check_docker():
        sys.exit(1)

    if not check_env_files():
        sys.exit(1)

    # Запускаем тесты
    success = run_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

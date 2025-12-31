# Интеграционные тесты job-bot

Интеграционные тесты проверяют работу job-bot API в изолированном docker-compose окружении.

## 🚀 Рекомендуемый способ запуска

```bash
# Из корня проекта job-platform
python run_integration_tests.py
```

Этот скрипт автоматически:
- Запускает изолированное тестовое окружение
- Ожидает готовности всех сервисов
- Запускает тесты во всех submodules
- Останавливает окружение после завершения

## 🔧 Ручной запуск

### Предварительные требования

1. **Docker и Docker Compose** установлены и запущены
2. **Переменные окружения** настроены (`.env.dev`, `.env.hh.dev`)
3. **База данных** доступна через тестовое окружение

### Запуск тестового окружения

```bash
# В корне проекта
docker-compose -f docker-compose.test.yml up -d

# Ожидание готовности (примерно 30-60 секунд)
```

### Запуск тестов

```bash
# Только интеграционные тесты бота
cd job-bot && python -m pytest tests/integration/ -v

# Только unit тесты
python -m pytest -m unit -v

# Все тесты бота
python -m pytest -v
```

### Остановка тестового окружения

```bash
# В корне проекта
docker-compose -f docker-compose.test.yml down -v
```

## 📋 Что проверяют интеграционные тесты

### 🔐 Эндпоинты авторизации

1. **`/api/v1/auth/login`** - доступность эндпоинта авторизации
2. **`/api/v1/auth/refresh`** - структура ответов для обновления токенов
3. **`/api/v1/auth/hh/login`** - редирект на HH.ru OAuth
4. **`/api/v1/auth/hh/callback`** - обработка OAuth callback

### 🌐 API доступность

1. **`/docs`** - Swagger документация
2. **`/openapi.json`** - OpenAPI схема
3. **CORS заголовки** - настройки CORS

## 🔄 Процесс работы

1. **🚀 Запуск окружения** - изолированные контейнеры (test_db, test_api)
2. **⏳ Ожидание готовности** - health checks всех сервисов (до 2.5 мин)
3. **🔍 Выполнение запросов** - реальные HTTP запросы к API
4. **✅ Проверка ответов** - валидация статусов и содержимого
5. **🧹 Очистка** - автоматическая остановка контейнеров

## ⚙️ Переменные окружения

- `API_BASE_URL` - URL API (по умолчанию: `http://localhost:8001`)

## 🚨 Обработка ошибок

При недоступности API тесты показывают логи контейнеров и завершаются с понятным сообщением.

## 💡 Примеры команд

```bash
# Подробный вывод
python run_integration_tests.py --verbose

# Без остановки контейнеров (для отладки)
python run_integration_tests.py --no-cleanup

# Ручной запуск конкретного теста
python -m pytest tests/integration/test_auth_integration.py::TestAuthIntegration::test_auth_login_endpoint_available -v -s
```

## 🔗 Связанные компоненты

- **`run_integration_tests.py`** - централизованный скрипт запуска
- **`docker-compose.test.yml`** - тестовое окружение
- **job_aggregator/tests/** - тесты API
- **job-bot/tests/integration/** - интеграционные тесты бота

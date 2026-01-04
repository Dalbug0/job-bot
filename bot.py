import asyncio
import hashlib
import secrets
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_email = State()


from api_facade import ApiFacade
from config import settings

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
api_facade = ApiFacade()

# Кэш пользователей в памяти (данные проверяются через API базы данных)
# Используется для оптимизации, основное хранение - в базе данных API
user_storage: Dict[int, Dict] = {}


def generate_password() -> str:
    """Генерировать случайный пароль"""
    return secrets.token_urlsafe(16)


async def get_or_create_user(telegram_user: types.User) -> Dict:
    """Получить или создать пользователя с проверкой через базу данных"""
    user_id = telegram_user.id

    # Всегда проверяем через базу данных (API), а не полагаемся на локальное хранилище
    try:
        # Проверяем, зарегистрирован ли пользователь в базе данных по telegram_id
        user_info = await api_facade.get_telegram_user_info(user_id)

        # Если user_info пустой, значит пользователь не найден
        if not user_info:
            raise Exception("User not found in database")

        # Пользователь найден в базе данных - обновляем локальное хранилище
        user_storage[user_id] = {
            "telegram_id": user_id,
            "username": telegram_user.username
            or user_info.get("telegram_username"),
            "first_name": telegram_user.first_name
            or user_info.get("first_name"),
            "last_name": telegram_user.last_name or user_info.get("last_name"),
            "email": None,  # Telegram пользователи не имеют email
            "internal_user_id": user_info[
                "id"
            ],  # В ответе поле называется "id"
            "is_registered": True,
            "registration_type": "telegram",
            "from_database": True,  # Флаг, что данные получены из БД
        }
        return user_storage[user_id]

    except Exception:
        # Пользователь не найден в базе данных - регистрируем нового
        try:
            registration_result = await api_facade.register_telegram_user(
                telegram_id=user_id,
                telegram_username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )

            user_storage[user_id] = {
                "telegram_id": user_id,
                "username": telegram_user.username,
                "first_name": telegram_user.first_name,
                "last_name": telegram_user.last_name,
                "email": None,  # Telegram пользователи не имеют email
                "internal_user_id": registration_result["user_id"],
                "is_registered": True,
                "registration_type": "telegram",
                "from_database": False,  # Данные только что зарегистрированы
            }
            return user_storage[user_id]

        except Exception as e:
            # Проверяем, не является ли ошибка конфликтом (пользователь уже существует)
            error_text = str(e).lower()
            if "already exists" in error_text or "conflict" in error_text:
                # Пользователь уже существует, но get_telegram_user_info его не нашел
                # Возможно, есть несогласованность в данных
                # Попробуем еще раз получить информацию
                try:
                    user_info = await api_facade.get_telegram_user_info(
                        user_id
                    )
                    if user_info:
                        user_storage[user_id] = {
                            "telegram_id": user_id,
                            "username": telegram_user.username
                            or user_info.get("telegram_username"),
                            "first_name": telegram_user.first_name
                            or user_info.get("first_name"),
                            "last_name": telegram_user.last_name
                            or user_info.get("last_name"),
                            "email": None,
                            "internal_user_id": user_info["id"],
                            "is_registered": True,
                            "registration_type": "telegram",
                            "from_database": True,
                        }
                        return user_storage[user_id]
                except Exception:
                    pass

            # Если регистрация не удалась по другой причине, создаем запись без регистрации
            user_storage[user_id] = {
                "telegram_id": user_id,
                "username": telegram_user.username,
                "first_name": telegram_user.first_name,
                "last_name": telegram_user.last_name,
                "email": None,
                "internal_user_id": None,
                "is_registered": False,
                "registration_type": None,
                "from_database": False,
            }
            return user_storage[user_id]


def update_user_email(telegram_id: int, email: str) -> None:
    """Обновить email пользователя"""
    if telegram_id in user_storage:
        user_storage[telegram_id]["email"] = email


def update_user_registration_status(
    telegram_id: int, internal_user_id: int
) -> None:
    """Обновить статус регистрации пользователя"""
    if telegram_id in user_storage:
        user_storage[telegram_id]["internal_user_id"] = internal_user_id
        user_storage[telegram_id]["is_registered"] = True


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user = await get_or_create_user(message.from_user)

    status = (
        "Зарегистрирован" if user["is_registered"] else "Не зарегистрирован"
    )
    hh_status = "Подключен" if user.get("internal_user_id") else "Не подключен"

    await message.answer(
        "Привет! Я JobBot. Я помогу тебе работать с вакансиями и резюме.\n\n"
        f"Ваш статус: {status}\n"
        f"HH.ru: {hh_status}\n\n"
        "Доступные команды:\n"
        "/register - зарегистрироваться в системе\n"
        "/login - получить ссылку на авторизацию HH.ru\n"
        "/check_hh_status - проверить статус HH.ru\n"
        "/me - информация о профиле\n"
        "/resumes - список резюме\n"
        "/select_resume <id> - выбрать активное резюме\n"
        "/publish_resume <id> - опубликовать/поднять резюме\n"
        "/vacancies - список вакансий\n"
        "/search - поиск вакансий по компании и локации\n"
        "/refresh - обновить токен доступа"
        "/hh_me - информация о профиле HH.ru"
    )


@dp.message(Command("register"))
async def register_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user)

    if user["is_registered"] and user.get("registration_type") == "telegram":
        await message.answer(
            "✅ Вы уже автоматически зарегистрированы через Telegram!"
        )
        return
    elif user["is_registered"]:
        await message.answer("Вы уже зарегистрированы в системе через email!")
        return

    # Если автоматическая регистрация не сработала, предлагаем ручную через email
    await message.answer(
        "Автоматическая регистрация не удалась. Для ручной регистрации нужен ваш email адрес.\n"
        "Пожалуйста, введите email:"
    )
    await state.set_state(RegistrationStates.waiting_for_email)


@dp.message(StateFilter(RegistrationStates.waiting_for_email))
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()

    # Простая валидация email
    if "@" not in email or "." not in email:
        await message.answer("Неверный формат email. Попробуйте еще раз:")
        return

    try:
        # Регистрируем пользователя через API
        telegram_user = message.from_user
        username = telegram_user.username or f"user_{telegram_user.id}"

        internal_user_id = await api_facade.register_user(
            username=username, email=email, telegram_id=telegram_user.id
        )

        # Обновляем локальное хранилище
        update_user_email(telegram_user.id, email)
        update_user_registration_status(telegram_user.id, internal_user_id)

        await message.answer(
            f"✅ Регистрация успешна!\n"
            f"Ваш внутренний ID: {internal_user_id}\n\n"
            f"Теперь вы можете подключить аккаунт HH.ru командой /login"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка регистрации: {str(e)}")

    await state.clear()


@dp.message(Command("login"))
async def login_handler(message: types.Message):
    user = await get_or_create_user(message.from_user)

    if not user["is_registered"]:
        await message.answer("❌ Сначала зарегистрируйтесь командой /register")
        return

    try:
        login_url = await api_facade.get_hh_login_url(user["internal_user_id"])
        if login_url:
            await message.answer(
                f"🔗 Перейдите по ссылке для авторизации HH.ru:\n{login_url}\n\n"
                "1. Откройте ссылку в браузере\n"
                "2. Войдите в свой аккаунт HH.ru\n"
                "3. Разрешите доступ приложению\n"
                "4. После успешной авторизации используйте команду /check_hh_status\n\n"
                "После подключения HH.ru вы сможете работать с резюме и вакансиями!"
            )
        else:
            await message.answer("❌ Не удалось получить ссылку авторизации")
    except Exception as e:
        await message.answer(
            f"❌ Не удалось получить ссылку на авторизацию: {str(e)}"
        )


@dp.message(Command("check_hh_status"))
async def check_hh_status_handler(message: types.Message):
    user = await get_or_create_user(message.from_user)

    if not user["is_registered"]:
        await message.answer("❌ Сначала зарегистрируйтесь командой /register")
        return

    # Устанавливаем internal_user_id для авторизации в API
    api_facade.set_internal_user_id(user["internal_user_id"])

    try:
        status = await api_facade.get_hh_token_status(user["internal_user_id"])
        if status.get("status") == "found":
            await message.answer(
                "✅ HH.ru успешно подключен!\n\n"
                "Теперь вы можете:\n"
                "/resumes - просмотреть резюме\n"
                "/select_resume <id> - выбрать активное резюме\n"
                "/publish_resume <id> - опубликовать резюме"
            )
        else:
            await message.answer(
                "❌ HH.ru не подключен.\n\n"
                "Используйте /login для получения ссылки авторизации, "
                "затем перейдите по ссылке и повторите эту команду."
            )
    except Exception as e:
        await message.answer(f"❌ Ошибка проверки статуса: {str(e)}")


@dp.message(Command("me"))
async def me_handler(message: types.Message):
    user = await get_or_create_user(message.from_user)

    text = "👤 Ваш профиль:\n"
    text += f"Telegram ID: {user['telegram_id']}\n"
    text += f"Username: @{user['username'] or 'N/A'}\n"
    text += f"Имя: {user['first_name'] or 'N/A'}\n"
    text += f"Фамилия: {user['last_name'] or 'N/A'}\n"

    registration_type = user.get("registration_type")
    if registration_type == "telegram":
        text += "Тип регистрации: 🔵 Telegram (автоматическая)\n"
    elif registration_type == "email":
        text += "Тип регистрации: 📧 Email\n"
    else:
        text += "Тип регистрации: ❌ Не зарегистрирован\n"

    if user["is_registered"]:
        text += f"Внутренний ID: {user['internal_user_id']}\n"
        if user["email"]:
            text += f"Email: {user['email']}\n"

        try:
            hh_status = await api_facade.get_hh_token_status(
                user["internal_user_id"]
            )
            if hh_status.get("status") == "found":
                text += "HH.ru: ✅ Подключен\n"
                text += f"Токен создан: {hh_status.get('created_at', 'N/A')}\n"
            else:
                text += "HH.ru: ❌ Не подключен\n"
        except Exception as e:
            text += f"HH.ru статус: Ошибка получения - {str(e)}\n"

    await message.answer(text)


@dp.message(Command("hh_me"))
async def hh_me_handler(message: types.Message):
    user = await get_or_create_user(message.from_user)

    if not user["is_registered"]:
        await message.answer("❌ Сначала зарегистрируйтесь командой /register")
        return

    api_facade.set_telegram_id(user["telegram_id"])

    try:
        hh_user_info = await api_facade.get_hh_user_info()
        text = "🏢 Информация о профиле HH.ru:\n"
        text += f"ID: {hh_user_info.get('id', 'N/A')}\n"
        text += f"Имя: {hh_user_info.get('first_name', 'N/A')}\n"
        text += f"Фамилия: {hh_user_info.get('last_name', 'N/A')}\n"
        text += f"Email: {hh_user_info.get('email', 'N/A')}\n"
        text += f"Телефон: {hh_user_info.get('phone', 'N/A')}\n"

        # Проверяем тип аккаунта
        if 'is_employer' in hh_user_info:
            if hh_user_info['is_employer']:
                text += "Тип аккаунта: 🏢 Работодатель\n"
            else:
                text += "Тип аккаунта: 👤 Соискатель\n"

        # Проверяем наличие резюме
        text += "\n📄 Проверка резюме:\n"
        try:
            resumes = await api_facade.get_resumes()
            items = resumes.get("items", [])
            if items:
                text += f"✅ Найдено резюме: {len(items)} шт.\n"
                for resume in items[:3]:  # Показываем максимум 3 резюме
                    title = resume.get('title', 'Без названия')
                    resume_id = resume.get('id', 'N/A')
                    text += f"  • {title} (ID: {resume_id})\n"
                if len(items) > 3:
                    text += f"  ... и ещё {len(items) - 3} резюме\n"
            else:
                text += "❌ Резюме не найдены\n"
                text += "💡 Создайте резюме на hh.ru, чтобы использовать функции бота\n"
        except Exception as e:
            text += f"❌ Ошибка проверки резюме: {str(e)}\n"

        await message.answer(text)
    except Exception as e:
        await message.answer(f"❌ Ошибка получения информации HH.ru: {str(e)}")


@dp.message(Command("refresh"))
async def refresh_handler(message: types.Message):
    try:
        result = await api_facade.refresh_access_token()
        await message.answer("✅ Токен доступа успешно обновлен!")
    except Exception as e:
        await message.answer(f"Не удалось обновить токен: {str(e)}")


@dp.message(Command("resumes"))
async def resumes_handler(message: types.Message):
    user = await get_or_create_user(message.from_user)

    if not user["is_registered"]:
        await message.answer("❌ Сначала зарегистрируйтесь командой /register")
        return

    # Устанавливаем telegram_id для авторизации в API
    api_facade.set_telegram_id(user["telegram_id"])

    try:
        resumes = await api_facade.get_resumes()
        text = "\n".join(
            [f"{r['title']} — {r['id']}" for r in resumes.get("items", [])]
        )
        await message.answer(f"Твои резюме:\n{text}")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


# 📋 Получение списка вакансий
@dp.message(Command("vacancies"))
async def vacancies_handler(message: types.Message):
    try:
        vacancies = await api_facade.get_vacancies()
        if vacancies:
            text = format_vacancies_list(vacancies)
            await message.answer(f"📋 Список вакансий:\n\n{text}")
        else:
            await message.answer("Вакансий пока нет.")
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении списка вакансий: {str(e)}"
        )


@dp.message(Command("search_vacancies"))
async def search_vacancies_handler(message: types.Message):
    await message.answer(
        "🔍 Поиск вакансий\n\n"
        "Используйте формат:\n"
        "/search [компания] [локация]\n\n"
        "Примеры:\n"
        "/search Yandex Москва\n"
        "/search Google\n"
        '/search "" Санкт-Петербург\n\n'
        "Оставьте параметр пустым, чтобы искать по всем значениям."
    )


@dp.message(Command("search"))
async def search_handler(message: types.Message):
    try:
        # Парсим аргументы: /search компания локация
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.answer(
                "Используйте формат: /search [компания] [локация]"
            )
            return

        company = None
        location = None

        if len(parts) >= 2:
            company = (
                parts[1] if parts[1] != '""' and parts[1] != "''" else None
            )
        if len(parts) >= 3:
            location = (
                parts[2] if parts[2] != '""' and parts[2] != "''" else None
            )

        vacancies = await api_facade.search_vacancies(
            company=company, location=location
        )

        if vacancies:
            text = format_vacancies_list(vacancies)
            search_info = ""
            if company:
                search_info += f"Компания: {company} "
            if location:
                search_info += f"Локация: {location}"
            if search_info:
                text = f"🔍 Результаты поиска ({search_info}):\n\n{text}"
            else:
                text = f"🔍 Все вакансии:\n\n{text}"

            await message.answer(text)
        else:
            await message.answer("По вашему запросу вакансий не найдено.")

    except Exception as e:
        await message.answer(f"❌ Ошибка при поиске вакансий: {str(e)}")


def format_vacancies_list(vacancies: list) -> str:
    """Форматировать список вакансий для отображения"""
    formatted = []
    for v in vacancies[:10]:  # Ограничиваем до 10 вакансий
        title = v.get("title", "N/A")
        company = v.get("company", "N/A")
        location = v.get("location", "N/A")
        salary = v.get("salary")

        # Форматируем зарплату
        salary_text = ""
        if salary:
            if isinstance(salary, dict):
                from_salary = salary.get("from")
                to_salary = salary.get("to")
                currency = salary.get("currency", "RUB")

                if from_salary and to_salary:
                    salary_text = f"💰 {from_salary}-{to_salary} {currency}"
                elif from_salary:
                    salary_text = f"💰 от {from_salary} {currency}"
                elif to_salary:
                    salary_text = f"💰 до {to_salary} {currency}"

        url = v.get("url", "")
        if url:
            url_text = f"🔗 {url}"
        else:
            url_text = ""

        vacancy_text = f"🏢 {title}\n📍 {company}"
        if location and location != "N/A":
            vacancy_text += f", {location}"
        if salary_text:
            vacancy_text += f"\n{salary_text}"
        if url_text:
            vacancy_text += f"\n{url_text}"

        formatted.append(vacancy_text)

    return "\n\n".join(formatted)


# ➕ Добавление вакансии
@dp.message(Command("add_vacancy"))
async def add_vacancy_handler(message: types.Message):
    # Ожидаем формат: /add_vacancy Название;Компания;Локация;Описание
    try:
        _, data = message.text.split(" ", 1)
        title, company, location, description = data.split(";")
    except ValueError:
        await message.answer(
            "Используй формат: /add_vacancy Название;Компания;Локация;Описание"
        )
        return

    try:
        vacancy = await api_facade.add_vacancy(
            title, company, location, description
        )
        await message.answer(
            f"Вакансия добавлена: {vacancy['id']} — {vacancy['title']}"
        )
    except Exception as e:
        await message.answer(f"Ошибка при добавлении вакансии: {str(e)}")


# ✏️ Обновление вакансии
@dp.message(Command("update_vacancy"))
async def update_vacancy_handler(message: types.Message):
    # Ожидаем формат: /update_vacancy ID;Название;Компания;Локация;Описание
    try:
        _, data = message.text.split(" ", 1)
        vacancy_id, title, company, location, description = data.split(";")
    except ValueError:
        await message.answer(
            "Используй формат: /update_vacancy ID;Название;Компания;Локация;Описание"
        )
        return

    try:
        vacancy = await api_facade.update_vacancy(
            vacancy_id, title, company, location, description
        )
        await message.answer(
            f"Вакансия обновлена: {vacancy['id']} — {vacancy['title']}"
        )
    except Exception as e:
        await message.answer(f"Ошибка при обновлении вакансии: {str(e)}")


# 📄 Выбор активного резюме
@dp.message(Command("select_resume"))
async def select_resume_handler(message: types.Message):
    user = await get_or_create_user(message.from_user)

    if not user["is_registered"]:
        await message.answer("❌ Сначала зарегистрируйтесь командой /register")
        return

    # Устанавливаем telegram_id для авторизации в API
    api_facade.set_telegram_id(user["telegram_id"])

    try:
        resume_id = message.text.split(maxsplit=1)[1]
    except IndexError:
        await message.answer("Используй формат: /select_resume <ID_резюме>")
        return

    try:
        result = await api_facade.select_resume(resume_id)
        await message.answer(f"Активное резюме установлено: {resume_id}")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


# 📢 Публикация/поднятие резюме
@dp.message(Command("publish_resume"))
async def publish_resume_handler(message: types.Message):
    user = await get_or_create_user(message.from_user)

    if not user["is_registered"]:
        await message.answer("❌ Сначала зарегистрируйтесь командой /register")
        return

    # Устанавливаем telegram_id для авторизации в API
    api_facade.set_telegram_id(user["telegram_id"])

    try:
        resume_id = message.text.split(maxsplit=1)[1]
    except IndexError:
        await message.answer("Используй формат: /publish_resume <ID_резюме>")
        return

    try:
        result = await api_facade.publish_resume(resume_id)
        await message.answer("Резюме успешно поднято!")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

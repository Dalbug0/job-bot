import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from api_facade import ApiFacade
from config import settings

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
api_facade = ApiFacade()


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Привет! Я JobBot. Я помогу тебе работать с вакансиями и резюме.\n\n"
        "Доступные команды:\n"
        "/login - получить ссылку на авторизацию\n"
        "/me - информация о профиле\n"
        "/resumes - список резюме\n"
        "/select_resume <id> - выбрать активное резюме\n"
        "/publish_resume <id> - опубликовать/поднять резюме\n"
        "/vacancies - список вакансий\n"
        "/refresh - обновить токен доступа"
    )


@dp.message(Command("login"))
async def login_handler(message: types.Message):
    try:
        login_url = await api_facade.get_login_url()
        await message.answer(
            f"Перейдите по ссылке для авторизации:\n{login_url}\n\n"
            "После авторизации используйте /me для проверки статуса."
        )
    except Exception as e:
        await message.answer(f"Не удалось получить ссылку на авторизацию: {str(e)}")


@dp.message(Command("me"))
async def me_handler(message: types.Message):
    try:
        user_info = await api_facade.get_me()
        text = f"👤 Ваш профиль:\nID: {user_info.get('id', 'N/A')}\nEmail: {user_info.get('email', 'N/A')}"
        await message.answer(text)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@dp.message(Command("refresh"))
async def refresh_handler(message: types.Message):
    try:
        result = await api_facade.refresh_access_token()
        await message.answer("✅ Токен доступа успешно обновлен!")
    except Exception as e:
        await message.answer(f"Не удалось обновить токен: {str(e)}")


@dp.message(Command("resumes"))
async def resumes_handler(message: types.Message):
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
            text = "\n".join(
                [
                    f"{v['id']}: {v['title']} ({v['company']}, {v['location']})"
                    for v in vacancies
                ]
            )
            await message.answer(f"Список вакансий:\n{text}")
        else:
            await message.answer("Вакансий пока нет.")
    except Exception as e:
        await message.answer(f"Ошибка при получении списка вакансий: {str(e)}")


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

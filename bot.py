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
        "Привет! Я JobBot. Я помогу тебе работать с вакансиями и резюме."
    )


@dp.message(Command("resumes"))
async def resumes_handler(message: types.Message):
    try:
        resumes = await api_facade.get_resumes()
        text = "\n".join(
            [f"{r['title']} — {r['id']}" for r in resumes.get("items", [])]
        )
        await message.answer(f"Твои резюме:\n{text}")
    except Exception as e:
        await message.answer(f"Не удалось получить резюме: {str(e)}")


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
        await message.answer(f"Не удалось выбрать резюме: {str(e)}")


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
        await message.answer(f"Не удалось опубликовать резюме: {str(e)}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

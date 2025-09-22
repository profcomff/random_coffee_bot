import re

from aiogram import types
from sqlalchemy import exists

from controllerBD.db_loader import Session
from controllerBD.models import Username, Users
from handlers.user.ban_check import check_id_in_ban_with_status
from loader import bot, logger


async def comment_validator(text):
    """Валидация поля комментария."""
    if 10 <= len(text) <= 500:
        return True
    return False


async def ban_validator(message: types.Message):
    """Валидация пользователя для добавления в бан."""
    success, db_id, result_message = await resolve_user_input_to_db_id(message.text)

    if not success:
        await bot.send_message(message.from_user.id, result_message)
        return False

    # Проверяем, не забаннен ли уже пользователь
    if await check_id_in_ban_with_status(db_id, 1):
        await bot.send_message(
            message.from_user.id, f"Пользователь уже забаннен. {result_message}"
        )
        return False

    logger.info(f"Валидация пройдена. {result_message}")
    # Сохраняем найденный DB ID в message.text для дальнейшего использования
    message.text = str(db_id)
    return True


async def unban_validator(message: types.Message):
    """Валидация пользователя для вывода из бана."""
    success, db_id, result_message = await resolve_user_input_to_db_id(message.text)

    if not success:
        await bot.send_message(message.from_user.id, result_message)
        return False

    # Проверяем, забаннен ли пользователь
    if not await check_id_in_ban_with_status(db_id, 1):
        await bot.send_message(
            message.from_user.id, f"Пользователь не забаннен. {result_message}"
        )
        return False

    logger.info(f"Валидация пройдена. {result_message}")
    # Сохраняем найденный DB ID в message.text для дальнейшего использования
    message.text = str(db_id)
    return True


async def resolve_user_input_to_db_id(user_input: str):
    """
    Пытается определить внутренний ID пользователя по различным типам ввода:
    - Внутренний ID базы данных (числовой)
    - Telegram ID (числовой, но больше)
    - Username (начинается с @)

    Возвращает кортеж (success: bool, db_id: int | None, message: str)
    """
    user_input = user_input.strip()

    with Session() as db_session:
        # Случай 1: Ввод - это username (начинается с @)
        if user_input.startswith("@"):
            username = user_input[1:]  # Убираем @
            user_record = (
                db_session.query(Username).filter(Username.username == username).first()
            )
            if user_record:
                return (
                    True,
                    user_record.id,
                    f"Найден пользователь с username @{username}",
                )
            return False, None, f"Пользователь с username @{username} не найден"

        # Случай 2: Числовой ввод
        if re.fullmatch(r"^\d{1,15}$", user_input):
            user_id = int(user_input)

            # Сначала проверяем, является ли это внутренним ID базы данных
            internal_user = db_session.query(Users).filter(Users.id == user_id).first()
            if internal_user:
                return (
                    True,
                    user_id,
                    f"Найден пользователь по внутреннему ID: {internal_user.name}",
                )

            # Если не найден как внутренний ID, проверяем как Telegram ID
            telegram_user = (
                db_session.query(Users).filter(Users.teleg_id == user_id).first()
            )
            if telegram_user:
                return (
                    True,
                    telegram_user.id,
                    f"Найден пользователь по Telegram ID: {telegram_user.name}",
                )

            return (
                False,
                None,
                f"Пользователь с ID {user_id} не найден ни в внутренней базе, ни среди Telegram ID",
            )

        return False, None, "Неверный формат ввода. Введите число (ID) или username с @"


async def check_id_in_base(user_id):
    """Проверяем пользователя на наличие в БД."""
    with Session() as db_session:
        is_exist = db_session.query(exists().where(Users.id == user_id)).scalar()
        if not is_exist:
            return False
        return True

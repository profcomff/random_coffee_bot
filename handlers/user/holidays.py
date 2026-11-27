from datetime import date, timedelta

from aiogram import types
from aiogram.dispatcher import Dispatcher

from controllerBD.db_loader import Session, engine
from controllerBD.models import Holidays, UserStatus
from handlers.decorators import user_handlers
from handlers.user.check_message import send_message
from handlers.user.get_info_from_table import (
    get_id_from_user_info_table,
    get_teleg_id_from_user_info_table,
)
from handlers.user.work_with_date import date_from_db_to_message
from keyboards.user import (
    holidays_length,
    indefinite_holidays_message,
    one_week_holidays_message,
    set_holiday_message,
    three_week_holidays_message,
    turn_off_holidays,
    two_week_holidays_message,
)
from loader import bot, logger

INDEFINITE_HOLIDAY = "Неопределенный срок"
holiday_engine = engine.execution_options(isolation_level="READ COMMITTED")


# @dp.message_handler(text=set_holiday_message)
@user_handlers
async def check_and_choice_holidays(message: types.Message):
    """Проверка и выбор срока каникул"""
    logger.info(
        f"Пользователь с TG_ID {message.from_user.id} "
        f"перешел к установке срока каникул"
    )
    await check_holidays_until(message.from_user.id)
    await bot.send_message(
        message.from_user.id,
        text="Выбери на какой срок ты хочешь установить каникулы",
        reply_markup=holidays_length(),
    )


def message_for_holidays(date_to_return):
    return (
        f"Ты установил каникулы до "
        f'{date_to_return.strftime("%d.%m.%Y")} '
        f"и начнёшь участвовать в "
        f"распределении с "
        f'{(date_to_return + timedelta(days=1)).strftime("%d.%m.%Y")}.'
    )


# @dp.message_handler(text=one_week_holidays_message)
@user_handlers
async def get_one_week_holidays(message: types.Message):
    """Установка каникул на 1 неделю"""
    date_to_return = date.today() + timedelta(days=7)
    await get_holidays(message, date_to_return)
    await bot.send_message(
        message.from_user.id, text=message_for_holidays(date_to_return)
    )


# @dp.message_handler(text=two_week_holidays_message)
@user_handlers
async def get_two_week_holidays(message: types.Message):
    """Установка каникул на 2 недели"""
    date_to_return = date.today() + timedelta(days=14)
    await get_holidays(message, date_to_return)
    await bot.send_message(
        message.from_user.id, text=message_for_holidays(date_to_return)
    )


# @dp.message_handler(text=three_week_holidays_message)
@user_handlers
async def get_three_week_holidays(message: types.Message):
    """Установка каникул на 3 недели"""
    date_to_return = date.today() + timedelta(days=21)
    await get_holidays(message, date_to_return)
    await bot.send_message(
        message.from_user.id, text=message_for_holidays(date_to_return)
    )


@user_handlers
async def get_indefinite_holidays(message: types.Message):
    """Пауза в подборе пар до ручного возобновления."""
    await get_holidays(message, INDEFINITE_HOLIDAY)
    await bot.send_message(
        message.from_user.id,
        text="Подбор пар приостановлен. Чтобы снова участвовать, нажми «Отключить» в меню «Каникулы».",
    )


# @dp.message_handler(text=turn_off_holidays)
@user_handlers
async def cancel_holidays(message: types.Message):
    """Отключение режима каникул"""
    teleg_id = message.from_user.id
    user_id = get_id_from_user_info_table(teleg_id)
    with Session(bind=holiday_engine) as db_session, db_session.begin():
        db_session.query(Holidays).filter(Holidays.id == user_id).update(
            {"status": 0, "till_date": "null"}
        )
        db_session.query(UserStatus).filter(UserStatus.id == user_id).update(
            {"status": 1}
        )
    await bot.send_message(teleg_id, text="Режим каникул был отключен")
    logger.info(f"Пользователь с TG_ID {teleg_id} отключил режим каникул")


async def get_holidays(message: types.Message, date_to_return):
    """Запись данных о каникулах в БД"""
    teleg_id = message.from_user.id
    user_id = get_id_from_user_info_table(teleg_id)
    with Session(bind=holiday_engine) as db_session, db_session.begin():
        db_session.query(Holidays).filter(Holidays.id == user_id).update(
            {"status": 1, "till_date": str(date_to_return)}
        )
        db_session.query(UserStatus).filter(UserStatus.id == user_id).update(
            {"status": 0}
        )
    logger.info(
        f"Пользователь с TG_ID {teleg_id} установил режим каникул: {date_to_return}"
    )


async def check_holidays_until(teleg_id):
    """Проверка даты окончания каникул пользователя в БД"""
    with Session() as db_session:
        user_id = get_id_from_user_info_table(teleg_id)
        row = db_session.query(Holidays).filter(Holidays.id == user_id).first().__dict__
        if row["status"] == 0:
            return
        if row["till_date"] == INDEFINITE_HOLIDAY:
            await bot.send_message(teleg_id, text="Каникулы включены без срока.")
        else:
            await bot.send_message(
                teleg_id,
                text=f"Каникулы установлены до "
                f'{date_from_db_to_message(row["till_date"])}.\n'
                f"Ты начнешь участвовать в распределении пар "
                f"со следующего дня.",
            )


async def sheduled_check_holidays():
    """Отключение режима каникул при окончании срока. Проверка по расписанию"""
    logger.info("Начало автопроверки статуса каникул")
    today = str(date.today())
    with Session() as db_session:
        expired_users = (
            db_session.query(Holidays.id).filter_by(status=1, till_date=today).all()
        )
    for (user_id,) in expired_users:
        with Session(bind=holiday_engine) as db_session, db_session.begin():
            if (
                not db_session.query(Holidays)
                .filter_by(id=user_id, status=1, till_date=today)
                .update({"status": 0, "till_date": "null"})
            ):
                continue
            db_session.query(UserStatus).filter(UserStatus.id == user_id).update(
                {"status": 1}
            )
        teleg_id = get_teleg_id_from_user_info_table(user_id)
        await send_message(teleg_id=teleg_id, text="Режим каникул был отключен")
        logger.info(f"Каникулы юзера {teleg_id} отключены автопроверкой")
    logger.info("Конец автопроверки статуса каникул")


def register_holidays_handlers(dp: Dispatcher):
    dp.register_message_handler(check_and_choice_holidays, text=set_holiday_message)
    dp.register_message_handler(get_one_week_holidays, text=one_week_holidays_message)
    dp.register_message_handler(get_two_week_holidays, text=two_week_holidays_message)
    dp.register_message_handler(
        get_three_week_holidays, text=three_week_holidays_message
    )
    dp.register_message_handler(
        get_indefinite_holidays, text=indefinite_holidays_message
    )
    dp.register_message_handler(cancel_holidays, text=turn_off_holidays)

from aiogram import exceptions, types
from aiogram.dispatcher import Dispatcher

from controllerBD.db_loader import Session
from controllerBD.models import MetInfo
from handlers.decorators import user_handlers
from handlers.user.add_username import check_username
from handlers.user.get_info_from_table import (
    get_full_user_info_by_id,
    get_holidays_status_from_db,
    get_id_from_user_info_table,
    get_user_data_from_db,
    get_user_status_from_db,
)
from handlers.user.new_member import get_gender_from_db, start_registration
from handlers.user.reviews import get_met_id_with_user_last_week
from handlers.user.work_with_date import date_from_db_to_message
from keyboards.user import *
from loader import bot, logger
from sendler import make_message


# @dp.errors_handler(exception=exceptions.RetryAfter)
async def exception_handler(update: types.Update, exception: exceptions.RetryAfter):
    await update.message.answer("Превышен лимит на данный запрос. " "Подожди 5 минут")
    logger.info(f"Пользователь {update.message.from_user.id} флудит")
    return True


# @dp.message_handler(text=[menu_message, back_to_menu])
@user_handlers
async def main_menu(message: types.Message):
    """Вывод меню"""
    await bot.send_message(
        message.from_user.id, text="Меню:", reply_markup=menu_markup(message)
    )


# @dp.message_handler(text=my_profile_message)
@user_handlers
async def send_profile(message: types.Message):
    """Вывод данных о пользователе"""
    await check_username(message)
    logger.info(
        f"Пользователь с TG_ID {message.from_user.id} " f"запросил информацию о себе"
    )
    data = dict(get_user_data_from_db(message.from_user.id))
    gender_id = data["gender"]
    gender_status = get_gender_from_db(gender_id)
    data["gender"] = gender_status
    if data["birthday"] != "Не указано":
        data["birthday"] = date_from_db_to_message(data["birthday"])
    await bot.send_message(
        message.from_user.id,
        f"Имя: {data['name']}\n"
        f"Дата рождения: {data['birthday']}\n"
        f"О себе: {data['about']}\n"
        f"Пол: {data['gender']}",
        reply_markup=edit_profile_markup(),
    )


# @dp.message_handler(text=edit_profile_message)
@user_handlers
async def edit_profile(message: types.Message):
    """Перенаправление на повторную регистрацию"""
    logger.info(
        f"Пользователь с TG_ID {message.from_user.id} "
        f"отправлен на повторную регистрацию"
    )
    await start_registration(message)


# @dp.message_handler(text=about_bot_message)
async def about_bot(message: types.Message):
    """Вывод информации о боте"""
    logger.info(
        f"Пользователь с TG_ID {message.from_user.id} " f"запросил информацию о боте"
    )
    await bot.send_message(
        message.from_user.id,
        """☕️ Алоха\, это бот Рандом Кофе\!

Бот еженедельно подбирает вам собеседника для очной или онлайн\-встречи\. Общайтесь\, делитесь идеями и расширяйте круг знакомств\!

*Как это работает\:*
— Алгоритм формирует пару *каждую неделю*\, стараясь избежать повторов\.
— После уведомления вы **самостоятельно договариваетесь** о времени и месте\.

*Правила\:*
— *Хотите отдохнуть\?* Включите «Каникулы» в настройках \(1\-3 недели\) *до* распределения пар\.
— Если пара уже назначена\, а вы не планируете встречаться — *предупредите партнёра* и\, например\, перенесите встречу\. Игнор — последний вариант\!
— Хотите перестать рандомкофиться\? Остановите бота через меню Telegram\.

*Советы\:*
— Идеальный формат\: *20–30 минут* за чашкой кофе или прогулкой\.
— *Очные встречи* предпочтительнее, но онлайн — допустимая альтернатива\.

По вопросам, идеям и предложениям\: @MArzangulyan
Пусть каждая встреча будет вдохновляющей\! 😊
""",
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
    )


# @dp.message_handler(text=my_status_message)
@user_handlers
async def status_message(message: types.Message):
    """Вывод статуса участия в распределении"""
    await check_username(message)
    logger.info(
        f"Пользователь с TG_ID {message.from_user.id} "
        f"запросил информацию о статусе участия"
    )
    user_row = get_user_data_from_db(message.from_user.id)
    status_row = get_user_status_from_db(user_row["id"])
    if status_row["status"] == 1:
        status = "Вы участвуете в распределении пар на следующей неделе"
    else:
        holidays_row = get_holidays_status_from_db(user_row["id"])
        till_value = holidays_row["till_date"]
        if till_value == "null" or till_value == "Неопределенный срок":
            holidays_till = "неопределенной даты"
        else:
            holidays_till = date_from_db_to_message(till_value)
        status = (
            f"Ты на каникулах до {holidays_till}. "
            f"В это время пара для встречи тебе предложена не будет. "
            f"После указанной даты статус 'Активен' "
            f"будет восстановлен автоматически. Если дата не "
            f"определена, то отключить каникулы необходимо "
            f"вручную кнопкой 'Отключить' в меню 'Каникулы'"
        )
    await bot.send_message(message.from_user.id, text=status)
    logger.info(
        f"Пользователь с TG_ID {message.from_user.id} "
        f"получил информацию о статусе участия"
    )


# @dp.message_handler(text=my_pare_button)
@user_handlers
async def my_pare_check(message: types.Message):
    await check_username(message)
    user_id = get_id_from_user_info_table(message.from_user.id)
    met_id = get_met_id_with_user_last_week(user_id)
    if met_id is None:
        await bot.send_message(
            message.from_user.id, "Ты не участвовал в последнем распределении."
        )
    else:
        with Session() as db_session:
            users = (
                db_session.query(MetInfo).filter(MetInfo.id == met_id[0]).first().__dict__
            )
            if users["first_user_id"] == user_id:
                user_info = get_full_user_info_by_id(users["second_user_id"])
            else:
                user_info = get_full_user_info_by_id(users["first_user_id"])
            message_text = make_message(user_info)
        try:
            await bot.send_message(
                message.from_user.id,
                message_text,
                parse_mode="HTML",
                reply_markup=help_texts_markup(),
            )
        except Exception as error:
            logger.error(
                f"Сообщение для пользователя {user_id} "
                f"не отправлено. Ошибка {error}"
            )
    logger.info(
        f"Пользователь с TG_ID {message.from_user.id} "
        f"получил информацию о своей паре"
    )


def register_user_handlers(dp: Dispatcher):
    dp.register_errors_handler(exception_handler, exception=exceptions.RetryAfter)
    dp.register_message_handler(main_menu, text=[menu_message, back_to_menu])
    dp.register_message_handler(send_profile, text=my_profile_message)
    dp.register_message_handler(edit_profile, text=edit_profile_message)
    dp.register_message_handler(about_bot, text=about_bot_message)
    dp.register_message_handler(status_message, text=my_status_message)
    dp.register_message_handler(my_pare_check, text=my_pare_button)

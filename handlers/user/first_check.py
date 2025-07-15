from aiogram import types
from aiogram.types import ReplyKeyboardRemove

from data import ADMIN_TG_ID, IS_FOR_BUR
from handlers.user.ban_check import check_user_in_ban
from handlers.user.get_info_from_table import check_user_in_base
from keyboards.admin import admin_main_markup
from keyboards.user import menu_markup, start_registr_markup
from loader import bot
from states import BannedState, UserData


async def check_and_add_registration_button(message: types.Message):
    """Проверка пользователя для последующих действий."""
    text = (
                "Добро пожаловать в бот!\n\n"
                "Для подбора пары нужно пройти небольшую регистрацию: "
                "представиться и ответить на пару вопросов о себе, "
                "чтобы собеседнику было проще начать с тобой разговор. Если"
                " отвечать не хочется, то часть шагов можно пропустить.\n\n"
                'Нажми кнопку "Регистрация" ниже.\n\n'
                "Для общения, помощи и рассказов о том, как прошла "
                "встреча присоединяйся к нашему IT сообществу в "
                "телеграм https://t.me/ViribusUnitisGroup"
            )
    if IS_FOR_BUR:
        text = (
            """
            Привет! Добро пожаловать в бот для знакомств 2-й смены лагеря "Буревестник" 2025!
            Каждый день мы будем подбирать для тебя нового собеседника из нашей смены. Ты сможешь узнать, кто это, и пойти познакомиться с ним вживую! Распределение происходит ежедневно, так что не упусти шанс найти новых друзей.
            Чтобы начать, пройди небольшую регистрацию: представься и ответь на пару вопросов. Это поможет твоему новому знакомому завязать разговор.
            Нажми кнопку "Регистрация" ниже, чтобы найти первого собеседника!
            Для общения всей сменой, помощи и рассказов о встречах присоединяйся к нашему общему чату в Телеграме: https://t.me/+Nrp4dllTGetkNDJi
            """
        )
    if not await check_user_in_base(message):
        await bot.send_message(
            message.from_user.id,
            text=text,
            reply_markup=start_registr_markup(),
        )
        await UserData.start.set()
    elif message.from_user.id in list(map(int, ADMIN_TG_ID.split())):
        await bot.send_message(
            message.from_user.id,
            text="Привет, Админ. Добро пожаловать в меню администратора",
            reply_markup=admin_main_markup(),
        )
    else:
        if not await check_user_in_ban(message):
            await bot.send_message(
                message.from_user.id,
                text="Воспользуйтесь меню",
                reply_markup=menu_markup(message),
            )
        else:
            await bot.send_message(
                message.from_user.id,
                text="К сожалению ты нарушил наши правила и попал в бан. "
                "Для решения данного вопроса обратись к "
                "администратору @Loravel",
                reply_markup=ReplyKeyboardRemove(),
            )
            await BannedState.start.set()

from aiogram.utils.exceptions import MessageToDeleteNotFound, MessageCantBeEdited, MessageNotModified

from constants import BOT_TOKEN
from aiogram import Bot, types, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

from db import UsersActions
from constants import UsersConstants, online_user_db


storage = MemoryStorage()

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)
print(bot, dp)


async def bot_delete_message(chat_id, message_id) -> bool:
    """
    удаляет сообщение из чата по его id
    :param chat_id: id чата
    :param message_id:  id сообщения
    :return: удалось или нет удалить сообщение
    """
    try:
        await bot.delete_message(chat_id, message_id)
        return True
    except MessageToDeleteNotFound as err:
        return False


async def bot_edit_message(**kwargs) -> bool:
    """
        Редактирует сообщение из чата по его id
        :param chat_id: id чата
        :param message_id:  id сообщения
        :return: удалось или нет отредактировать сообщение
    """
    try:
        await bot.edit_message_text(
            chat_id=kwargs.get('chat_id', None), message_id=kwargs.get('message_id', None),
            text=kwargs.get('text', None), reply_markup=kwargs.get('reply_markup', None)
        )
        return True
    except (MessageCantBeEdited, MessageNotModified) as err:
        return False


async def get_current_state(user_id: int = None, chat_id: int = None) -> FSMContext:
    """
    Возвращает текущее состояние FSM.
    """
    # return dp.current_state(user=user_id, chat=chat_id)
    return dp.get_current().current_state(user=user_id)


async def constants_set(user_id: int = None) -> None:
    """
    Читает из БД конфигурацию пользователя, если она там есть и записывает в онлайн хранилище online_user_db
    Если пользователь новый, у него нет записи БД конфигураций, то она создается с конфигурацией по дефолту.
    """
    if user_id:
        storage_db = UsersActions()
        user_set = storage_db.get_user_constant(user_id)
        if user_set:
            online_user_db.update({user_id: UsersConstants(*user_set)})
        else:
            online_user_db.update({user_id: UsersConstants()})
            default_const_user = online_user_db.get(user_id, None)
            storage_db.init_user_constant(
                user_id,
                default_const_user.IMAGE_SIZE,
                default_const_user.RESULT_SIZE,
                default_const_user.STORY_SIZE
            )

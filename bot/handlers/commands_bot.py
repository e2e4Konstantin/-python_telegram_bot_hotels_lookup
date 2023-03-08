from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

import re
from typing import Union

from db import UsersActions
from constants import LEXICON, RE_DIGITS, MAX_IMAGE_SIZE, MAX_RESULT_SIZE, MAX_STORY_SIZE
from constants import online_user_db

from bot.define_bot import bot, constants_set


class FSMconfigForm(StatesGroup):
    """
        Состояния для изменения констант пользователя.
        Экземпляры класса State - возможные состояния,
        в которых будет находиться бот при заполнении данных.
        Состояния диалога для получения:

        fill_constants: Новые константы

    """
    fill_constants = State()


async def start_command(message: types.Message, state: FSMContext):
    """ Хэндлер для перезапуска бота. Будет срабатывать на команду /start. """
    try:
        await message.answer(text=f"<b>{message.from_user.first_name}</b> {LEXICON['/start']}")
        await message.answer(text=LEXICON['/help_info'])
        await message.delete()

        await constants_set(message.from_user.id)

        await state.finish()
        await state.reset_state()
    except Exception as err:
        print("start_command", err)
        await message.reply("пиши сюда https://t.me/HotelsLookerBot")


async def help_command(message: types.Message):
    """ Хэндлер для вывода возможностей и команд бота. Будет срабатывать на команду /help. """
    await bot.send_message(message.from_user.id, f"{LEXICON['/help_command']}")
    await message.delete()


def create_config_string(image_size: int = 0, result_size: int = 0, story_size: int = 0) -> Union[str, None]:
    """ Создает текстовое сообщение для показа текущей конфигурации пользователя """
    if image_size > 0 and result_size > 0 and story_size > 0:
        return f"{LEXICON['config_image']} {image_size}\n" \
               f"{LEXICON['config_hotels']} {result_size}\n" \
               f"{LEXICON['config_history']} {story_size}\n\n{LEXICON['config_setting']}"
    return None


async def config_command(message: types.Message):
    """
    Хэндлер будет срабатывать на команду /config.
    Выводит сообщение с текущей конфигурацией пользователя.
    Если ее нет, то она создается по дефолту в оперативном хранилище и в БД constants_set().
    """
    config_line = ""
    if online_user_db.get(message.from_user.id, None) is None:
        await constants_set(message.from_user.id)

    user_config = online_user_db.get(message.from_user.id, None)
    if user_config:
        config_line = create_config_string(user_config.IMAGE_SIZE, user_config.RESULT_SIZE, user_config.STORY_SIZE)
    else:
        print(f"\t--->>> config_command: что-то не тот")
    await bot.send_message(message.from_user.id, f"{LEXICON['/config']}{config_line}")


async def customising_command(message: types.Message, state: FSMContext):
    """
    Хэндлер будет срабатывать на команду /customising и
    переводить бота в состояние ожидания ввода констант
    """
    await message.answer(text=f"{LEXICON['/customising']}{LEXICON['info_constant']}")
    await FSMconfigForm.fill_constants.set()


def check_constants_string(constants_src: str):
    """
    Выделяет из входной строки три числа.
    :param constants_src: Входная строка.
    :return: Кортеж с полученными числами
    """
    digits_pattern = re.compile(RE_DIGITS)
    constants = digits_pattern.findall(constants_src)
    constants_digits = list(map(int, constants))[:3]
    if len(constants_digits) == 3 \
            and 0 < constants_digits[0] <= MAX_IMAGE_SIZE \
            and 0 < constants_digits[1] <= MAX_RESULT_SIZE \
            and 0 < constants_digits[2] <= MAX_STORY_SIZE:
        return constants_digits[0], constants_digits[1], constants_digits[2]
    return None


async def constants_sent(message: types.Message, state: FSMContext):
    """
    Хэндлер сработает, если введены правильные константы.
    Сохраняет введенное название в словарь FSM data с ключом 'constants_line'.

    """
    src_result = check_constants_string(message.text)
    if src_result:
        await state.finish()
        await state.reset_state()
        await message.delete()

        user_config = online_user_db.get(message.from_user.id)

        user_config.IMAGE_SIZE = src_result[0]
        user_config.RESULT_SIZE = src_result[1]
        user_config.STORY_SIZE = src_result[2]

        storage = UsersActions()
        storage.set_user_constant(message.from_user.id, src_result[0], src_result[1], src_result[2])
        # storage.inform_db()
        await config_command(message)
    else:
        await warning_not_constants(message, state)


async def warning_not_constants(message: types.Message, state: FSMContext):
    """  Хэндлер сработает, если во время ввода констант будет введено что-то некорректное"""
    await message.answer(text=f"{LEXICON['wrong_constant']}{LEXICON['info_constant']}")
    await message.delete()
    await FSMconfigForm.fill_constants.set()

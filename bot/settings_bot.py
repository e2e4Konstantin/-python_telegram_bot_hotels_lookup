from aiogram import types, Dispatcher
from aiogram.dispatcher import filters

from bot.handlers import commands_bot, machine_bot
from constants import RE_DATE, RE_DIGITS, RE_NAME_REGION, SORT_LIST
import re

async def set_main_menu(disp: Dispatcher) -> None:
    """ Создаем кнопку меню. """
    bot_commands = [
        types.BotCommand(command="/start", description="запуск бота"),
        types.BotCommand(command="/fillform", description="поиск отеля"),
        types.BotCommand(command="/showdata", description="информация об отеле"),
        types.BotCommand(command="/showimage", description="фотографии отеля"),
        types.BotCommand(command="/cancel", description="прервать запрос"),
        types.BotCommand(command="/history", description="история поисков"),

        types.BotCommand(command="/help", description="как управлять"),
        types.BotCommand(command="/config", description="конфигурация")
    ]
    await disp.bot.set_my_commands(bot_commands)


def register_region_handlers(dispatcher: Dispatcher) -> None:
    """
        Создаем диалог для получения id региона.
        Запрашиваем название региона, ищем это название в API hotels.
        Из найденных вариантов, создаем меню для выбора.
        По выбору из меню выделяем id региона.
        Записываем id вместе с полной информацией по выбранному региону.
    """

    def check_name(text: str = "") -> bool:
        """
            Название региона должно состоять из допустимых символов RE_NAME_REGION.
            Если в строке найдены другие символы, то имя ошибочное.
        """
        if text:
            invalid_characters = re.sub(RE_NAME_REGION, "", text.strip().lower())
            return False if invalid_characters else True
        return False

    dispatcher.register_message_handler(
        machine_bot.region_name_sent,
        lambda x: check_name(x.text),
        content_types=types.ContentType.TEXT,
        state=machine_bot.FSMRequestForm.fill_region
    )
    dispatcher.register_message_handler(
        machine_bot.warning_not_region,
        content_types='any',
        state=machine_bot.FSMRequestForm.fill_region
    )
    dispatcher.register_message_handler(
        machine_bot.region_index_choice,
        lambda x: re.fullmatch(RE_DIGITS, x.text.strip()) is not None,
        content_types=types.ContentType.TEXT,
        state=machine_bot.FSMRequestForm.fill_region_id
    )
    dispatcher.register_message_handler(
        machine_bot.warning_not_region_index,
        content_types='any',
        state=machine_bot.FSMRequestForm.fill_region_id
    )


def register_dates_handlers(dispatcher: Dispatcher) -> None:
    """
        Создаем диалог для получения дат въезда и выезда
    """
    dispatcher.register_message_handler(
        machine_bot.process_dates_sent,
        filters.Regexp(RE_DATE),
        content_types=types.ContentType.TEXT,
        state=machine_bot.FSMRequestForm.fill_dates
    )
    dispatcher.register_message_handler(
        machine_bot.warning_not_dates,
        content_types='any',
        state=machine_bot.FSMRequestForm.fill_dates
    )


def register_adults_handlers(dispatcher: Dispatcher) -> None:
    """ Создаем диалог для получения количества взрослых путешественников. """
    dispatcher.register_message_handler(
        machine_bot.process_adults_sent,
        lambda x: re.fullmatch(RE_DIGITS, x.text.strip()) is not None,
        content_types=types.ContentType.TEXT,
        state=machine_bot.FSMRequestForm.fill_adults
    )
    dispatcher.register_message_handler(
        machine_bot.warning_not_adults, content_types='any',
        state=machine_bot.FSMRequestForm.fill_adults
    )


def register_children_handlers(dispatcher: Dispatcher) -> None:
    """ Создаем диалог для получения количества детей. """
    dispatcher.register_message_handler(
        machine_bot.process_children_sent,
        filters.Regexp(RE_DIGITS),
        content_types=types.ContentType.TEXT,
        state=machine_bot.FSMRequestForm.fill_children
    )
    dispatcher.register_message_handler(
        machine_bot.warning_not_children,
        content_types='any',
        state=machine_bot.FSMRequestForm.fill_children
    )


def register_hotel_handlers(dispatcher: Dispatcher) -> None:
    """
        Создаем диалог для создания меню по которому получим id отеля.
        Даем возможность сортировки.
        Получаем ответ из меню выбора отеля из которого выделим id отеля
        Показываем результат.
    """
    dispatcher.register_message_handler(
        machine_bot.hotel_index_choice,
        lambda x: re.fullmatch(RE_DIGITS, x.text.strip()) is not None,
        content_types=types.ContentType.TEXT,
        state=machine_bot.FSMRequestForm.fill_hotel
    )
    dispatcher.register_message_handler(
        machine_bot.hotels_sort,
        commands=SORT_LIST,
        state=machine_bot.FSMRequestForm.fill_hotel
    )

    dispatcher.register_callback_query_handler(
        machine_bot.hotels_sort_buttons,
        filters.Text(equals=SORT_LIST, ignore_case=True),
        state=machine_bot.FSMRequestForm.fill_hotel
    )

    dispatcher.register_callback_query_handler(
        machine_bot.show_image_callback,
        filters.Text(startswith="show_image", ignore_case=True),
        state="*"
    )

    dispatcher.register_message_handler(
        machine_bot.warning_not_hotel_index,
        content_types='any',
        state=machine_bot.FSMRequestForm.fill_hotel
    )


def register_config_handlers(dispatcher: Dispatcher) -> None:
    """
        Создаем диалог для изменения констант/конфиг.
    """

    dispatcher.register_message_handler(
        commands_bot.constants_sent,
        lambda x: re.findall(RE_DIGITS, x.text.strip()) is not None,
        content_types=types.ContentType.TEXT,
        state=commands_bot.FSMconfigForm.fill_constants
    )
    dispatcher.register_message_handler(
        commands_bot.warning_not_constants,
        content_types='any',
        state=commands_bot.FSMconfigForm.fill_constants
    )


def register_all_handlers(disp: Dispatcher) -> None:
    """ Регистрируем хэндлеры. """
    disp.register_message_handler(commands_bot.start_command, filters.CommandStart(), state='*')
    disp.register_message_handler(commands_bot.help_command, filters.CommandHelp())
    disp.register_message_handler(commands_bot.config_command, commands=['config'], state='*')
    disp.register_message_handler(machine_bot.fillform_command, commands=['fillform'], state='*')
    disp.register_message_handler(machine_bot.cancel_command, commands='cancel', state='*')
    disp.register_message_handler(machine_bot.showdata_command, commands='showdata', state='*')
    disp.register_message_handler(machine_bot.show_image_command, commands='showimage', state='*')
    disp.register_message_handler(machine_bot.history_command, commands='history', state='*')
    disp.register_message_handler(commands_bot.customising_command, commands='customising', state='*')

    register_region_handlers(disp)
    register_dates_handlers(disp)
    register_adults_handlers(disp)
    register_children_handlers(disp)
    register_hotel_handlers(disp)
    register_config_handlers(disp)

    disp.register_message_handler(machine_bot.send_answer)



from datetime import datetime, date
import time
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
import re
import json

from typing import Union, List, Tuple

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.storage import FSMContextProxy

from aiogram.dispatcher.filters.state import State, StatesGroup

from aiogram.types.input_media import InputMediaPhoto

from constants import LEXICON, RE_DIGITS, RE_DATE, TRANSLATE_REGION_DICT, SORT_LIST
from constants import MAX_ADULTS, MIN_AGE_CHILD, MAX_AGE_CHILD, MAX_CHILDREN, MAX_DAYS
from constants import USE_TMP_FILE, MAX_STORY_SIZE, MAX_RESULT_SIZE

from constants import online_user_db

import site_api
from settingsAPI import create_file_name

from bot.keyboards import inline_keyboards
from bot.define_bot import bot_delete_message, bot_edit_message, constants_set

""" БД для хранения исторических данных полученных от пользователя и его конфигурации. """
from db import UsersActions


class FSMRequestForm(StatesGroup):
    """
        Состояния для ввода данных пользователя.
        Экземпляры класса State - возможные состояния, в которых будет находиться бот при заполнении данных.
        Состояния диалога для получения:
        fill_region:        имени региона
        fill_region_id:     id региона
        fill_dates:         даты заезда и отъезда
        fill_adults:        количества взрослых путешественников
        fill_children:      количества детей
        fill_hotel:         отеля из предложенных вариантов

        используемые в диалоге ключи, те что со звездочками после закрытия диалога, удаляются:

        'region_name', 'region_info', 'dates', 'adults', 'children', 'hotel', 'hotel_info', 'hotel_url'
        ***'invitation_message', 'region_list', 'hotels_list', 'hotels_menu'
    """
    fill_region = State()
    fill_region_id = State()
    fill_dates = State()
    fill_adults = State()
    fill_children = State()
    fill_hotel = State()


""" формируем список возможных состояний FSMRequestFor"""
states_request_form = list(map(lambda x: f"FSMRequestForm.{x}", [x for x in dir(FSMRequestForm) if x[:4] == 'fill']))


async def send_answer(message: types.Message):
    """Хэндлер для сообщений которые не попали ни под какие другие фильтры"""
    await message.answer(text=LEXICON['other_answer'])


async def fillform_command(message: types.Message):
    """
    Хэндлер будет срабатывать на команду /fillform и
    переводить бота в состояние ожидания ввода региона
    очищает данные предыдущего запроса иначе читает константы из БД
    """
    await message.answer(text=LEXICON['/fillform'] + LEXICON['/cancel'])
    await FSMRequestForm.fill_region.set()

    user_config = online_user_db.get(message.from_user.id, None)
    if user_config:
        if user_config.last_query_data:
            user_config.last_query_data.clear()
    else:
        await constants_set(message.from_user.id)


def make_places_menu(regions: list = None) -> Union[str, None]:
    """
    Создает текст/меню с номерами регионов для выбора пользователем номера нужного региона.
    Вставляет русский перевод типов регионов.
    :param regions: Список регионов полученных из API hotels.com
    :return: строку/текст для создания сообщения меню со списком регионов и номеров/индексов.
    """
    if regions:
        out_text = [
            f"<b>{index + 1}</b>.\t{region_i['name']}, {TRANSLATE_REGION_DICT.get(region_i['type'], '')}"
            for index, region_i in enumerate(regions)
        ]
        return "\n".join(out_text)
    return None


def request_region_name(data: FSMContextProxy) -> list:
    """
    Получает с API Hotels.com список доступных регионов.
    Если в constants.py установлен USE_TMP_FILE, то для экономии трафика
    данные берутся из ранее записанного файла.
    :param data: Текущий словарь машины состояний.
    :return: Список регионов
    """
    region_name = data.get('region_name', "") if 'region_name' in data else ""
    if region_name:
        json_file_name = create_file_name(region_name, relative_position=".") if USE_TMP_FILE else None
        places = site_api.get_places_list(target_place=region_name, file_name=json_file_name, not_debug=False)
        if places:
            # site_api.show_places(places)
            return places
    return []


async def region_name_sent(message: types.Message, state: FSMContext):
    """
    Хэндлер сработает, если введено корректное название региона.
    Сохраняет введенное название в словарь FSM data с ключом 'region_name'.
    Запускает процесс поиска региона на API Hotels.
    Запоминает список найденных регионов во временный словарь data с ключом 'region_list'.
    Выводит сообщение с меню выбора номера найденных регионов.
    Переводит машину состояний в ожидание ввода индекса региона 'fill_region_id'.
    """
    async with state.proxy() as data:
        data['region_name'] = message.text.strip().lower()
        await delete_swear_message_chat(data)
        await message.answer(text=f"{LEXICON['look_region']} <b>{data['region_name'].title()}</b>\n{LEXICON['wait']}")

        places = request_region_name(data)

        if places:
            data['region_list'] = places
            data['invitation_message'] = await message.answer(
                text=LEXICON['choice_region'] + make_places_menu(places) + LEXICON['/cancel']
            )
            await FSMRequestForm.fill_region_id.set()
            await message.delete()
        else:
            data['region_list'] = None
            await message.answer(text=LEXICON['no_find_region'])
            await FSMRequestForm.fill_region.set()


async def warning_not_region(message: types.Message, state: FSMContext):
    """ Хэндлер сработает, если во время ввода имени региона будет введено что-то некорректное.  """
    async with state.proxy() as data:
        swear_word = LEXICON['swear_word'] if await delete_swear_message_chat(data) else ""
        data['swear_message'] = await message.answer(
            text=f"{swear_word}<b>{message.text.strip()[:10]}</b> "
                 f"{LEXICON['wrong_region']}{LEXICON['/cancel']}"
        )
    await message.delete()
    await FSMRequestForm.fill_region.set()


async def delete_swear_message_chat(data: FSMContextProxy) -> bool:
    """
    Если в словаре data есть 'swear_message', то удаляет его из чата
    :param data: прокси словарь машины состояний.
    :return: True если сообщение удалено
    """
    swear_message = data.get('swear_message', None)
    if swear_message:
        return await bot_delete_message(swear_message.chat.id, swear_message.message_id)
    return False


async def region_index_choice(message: types.Message, state: FSMContext):
    """
        Хэндлер сработает, если введен корректный индекс региона из меню.
        Проверяет полученное число/индекс меню, оно должно быть 'внутри' меню.
        Сохраняет в словарь data с ключом 'region_info' информацию по выбранному региону.
        Удаляет меню регионов из чата.
        Формирует строку дат для копирования, текущая дата+1 неделя, от нее еще 4 дня.
        Предлагает ввести даты.
        Переводит машину состояний в состояние ожидания ввода дат заезда и отъезда 'fill_date'.
    """
    current_state = await state.get_state()

    index_index = int(message.text.strip())
    async with state.proxy() as data:
        len_regions = len(data['region_list'])

    # len_regions = len(dict(await state.get_data())['region_list'])

    if 1 <= index_index <= len_regions:
        async with state.proxy() as data:
            data['region_info'] = data['region_list'][index_index - 1]
            data.pop('region_list', None)
            await delete_swear_message_chat(data)
            await bot_delete_message(
                chat_id=data['invitation_message'].chat.id,
                message_id=data['invitation_message'].message_id
            )
            data['invitation_message'] = await message.answer(
                text=f"{LEXICON['final_region']} <b>{data['region_info']['name']}</b> "
                     f"{TRANSLATE_REGION_DICT.get(data['region_info']['type'], '')}"
            )
            today = date.today()
            check_in_date = (today + relativedelta(weeks=+1)).strftime("%d/%m/%y")
            check_out_date = (today + relativedelta(weeks=+1, days=+4)).strftime("%d/%m/%y")
            samples = f"<code>{check_in_date} {check_out_date}</code>"
            data['invitation_message'] = await message.answer(
                text=f"{LEXICON['input_dates']}{samples}")
        await FSMRequestForm.fill_dates.set()
        await message.delete()
    else:
        await warning_not_region_index(message, state)
        await FSMRequestForm.fill_region_id.set()


async def warning_not_region_index(message: types.Message, state: FSMContext):
    """  Хэндлер сработает, если во время ввода индекса региона будет введено что-то некорректное"""
    async with state.proxy() as data:
        len_menu = len(data['region_list'])
        swear_word = LEXICON['swear_word'] if await delete_swear_message_chat(data) else ""
        data['swear_message'] = await message.answer(
            text=f"{swear_word}{LEXICON['wrong_number_region']} {len_menu}{LEXICON['/cancel']}")
    await message.delete()
    await FSMRequestForm.fill_region_id.set()


def valid_date_string_to_list(src_dates: str) -> List[str]:
    """
    Выделяет из входящей строки подстроки похожие на даты.
    Пробует из этих подстрок создать даты <class 'datetime.datetime'>.
    :param src_dates: исследуемая строка.
    :return: список текстовых дат в формате %d/%m/%Y.
    """
    date_regex = re.compile(RE_DATE)
    dates_in = date_regex.findall(src_dates)
    dates_out = []
    for date_i in dates_in:
        try:
            a = parse(date_i, dayfirst=True)
            dates_out.append(a.strftime("%d/%m/%Y"))
        except ValueError as err:
            pass
    return dates_out


async def process_dates_sent(message: types.Message, state: FSMContext):
    """
    Хэндлер сработает, если введен текст с данными похожими на даты.
    Проверяет, введено 2 даты, сохраняет эти даты списком в словарь data с ключом 'dates'.
    Вычисляет количество дней между введенными датами.
    Переводит машину состояний в состояние ожидания ввода количества взрослых 'fill_adults'.
    """
    dates_entered: List[str] = valid_date_string_to_list(message.text)
    if len(dates_entered) < 2:
        await warning_not_dates(message, state)
        await FSMRequestForm.fill_dates.set()
    else:
        check_in_date_src: str = dates_entered[0]
        check_out_date_src: str = dates_entered[1]

        check_in_date: datetime = parse(check_in_date_src, dayfirst=True)
        check_out_date: datetime = parse(check_out_date_src, dayfirst=True)

        days_numb = (check_out_date - check_in_date).days + 1

        if check_in_date <= check_out_date and 1 <= days_numb <= MAX_DAYS:
            await message.answer(
                text=f"{LEXICON['result_dates']}{LEXICON['check_in_date']} <b>{check_in_date_src.replace('/', '.')}</b>\n"
                     f"{LEXICON['check_out_date']} <b>{check_out_date_src.replace('/', '.')}</b>\n"
                     f"ночей: <b>{days_numb}</b>")
            async with state.proxy() as data:
                await delete_swear_message_chat(data)
                data['dates'] = [check_in_date_src, check_out_date_src]
                await bot_delete_message(
                    chat_id=data['invitation_message'].chat.id,
                    message_id=data['invitation_message'].message_id
                )
                data['invitation_message'] = await message.answer(text=LEXICON['input_adults'])
            await message.delete()
            await FSMRequestForm.fill_adults.set()
        else:
            await warning_not_dates(message, state)
            await FSMRequestForm.fill_dates.set()


async def warning_not_dates(message: types.Message, state: FSMContext):
    """  Хэндлер сработает, если во время ввода дат будет введено что-то некорректное"""
    async with state.proxy() as data:
        swear_word = LEXICON['swear_word'] if await delete_swear_message_chat(data) else ""
        data['swear_message'] = await message.answer(text=f"{swear_word}{LEXICON['wrong_dates']}{LEXICON['/cancel']}")
    await message.delete()
    await FSMRequestForm.fill_dates.set()


async def process_adults_sent(message: types.Message, state: FSMContext):
    """
    Хэндлер сработает, если введено число.
    Проверяет чтоб было введено правильное количество взрослых,
    сохраняет количество взрослых в словарь data с ключом 'adults'.
    Переводит машину состояний в состояние ожидания ввода возраста детей 'fill_children'.
    """
    adults_number = int(message.text.strip())
    if 0 < adults_number <= MAX_ADULTS:
        await message.answer(text=f"{LEXICON['result_adults']} <b>{adults_number}</b>")
        async with state.proxy() as data:
            await delete_swear_message_chat(data)
            data['adults'] = adults_number
            await bot_delete_message(
                chat_id=data['invitation_message'].chat.id,
                message_id=data['invitation_message'].message_id
            )
            data['invitation_message'] = await message.answer(text=LEXICON['input_children'])
        await FSMRequestForm.fill_children.set()
        await message.delete()
    else:
        await warning_not_adults(message, state)
        await FSMRequestForm.fill_adults.set()


async def warning_not_adults(message: types.Message, state: FSMContext):
    """  Хэндлер сработает, если во время ввода количество взрослых туристов будет введено что-то некорректное """
    current_state = await state.get_state()
    async with state.proxy() as data:
        swear_word = LEXICON['swear_word'] if await delete_swear_message_chat(data) else ""
        data['swear_message'] = await message.answer(text=f"{swear_word}{LEXICON['wrong_adults']}{LEXICON['/cancel']}")
    await message.delete()
    await FSMRequestForm.fill_adults.set()


def check_children_string(children_src: str) -> Tuple[bool, list]:
    """
    Выделяет из входной строки с возрастами детей легитимные числа указывающие возраст.
    :param children_src: входная строка.
    :return: кортеж с первым значением True, если все возраста детей введены корректно
    и вторым значением целочисленный список возрастов. Если детей нет, то возвращается пустой список.
    False если есть некорректные значения возраста и некорректный список.
    """
    digits_pattern = re.compile(RE_DIGITS)
    raw_children = digits_pattern.findall(children_src)
    children: List[int] = list(map(int, raw_children))
    children_unique = set(children)
    if not (len(children_unique) == 1 and list(children_unique)[0] == 0):
        valid_children = [x for x in children if MIN_AGE_CHILD <= x < MAX_AGE_CHILD][:MAX_CHILDREN]
        broken_ages = [x for x in children if x not in valid_children]
        if broken_ages:
            return False, broken_ages
        if valid_children:
            return True, valid_children
    return True, []


def make_children_string(children: List[int]) -> str:
    """
    Создает читабельную строку для вывода пользователю.
    'детей: 2. возраст: 3, 6 лет'
    :param children: список возрастов детей.
    :return: Текстовую информационную строку с количеством и возрастом детей
    """
    children_info = ""
    if children:
        children.sort()
        children_number = len(children)
        oldest_child = children[-1]
        if children_number == 1 and oldest_child == 1:
            oldest_info = "год"
        else:
            oldest_info = "года" if oldest_child < 5 else "лет"
        children_info = ', '.join([str(x) for x in children])
        children_info = f"детей: <b>{children_number}</b>. возраст: <b>{children_info}</b> {oldest_info}"
    return children_info


async def request_hotel_data(user_id: int, data: FSMContextProxy, sort_method: str = SORT_LIST[0]) -> list:
    """
    Получает с API Hotels.com список доступных отелей, сортирует список по умолчанию возрастанию цены.
    :param user_id: id пользователя.
    :param data: машина состояний.
    :param sort_method: метод сортировки списка отелей.
    :return: список отелей
    """
    region_id = data['region_info'].get('id', "") if 'region_info' in data else ""

    if region_id:
        region_name = data.get('region_name', "")
        json_file_name = create_file_name(region_id, region_name, relative_position=".") if USE_TMP_FILE else None

        if online_user_db.get(user_id, None) is None:
            await constants_set(user_id)
        user_config = online_user_db.get(user_id, None)
        if user_config:
            result_size = user_config.RESULT_SIZE
        else:
            result_size = MAX_RESULT_SIZE

        hotels = site_api.get_hotels_list(
            region_id=region_id, in_date=data['dates'][0], out_date=data['dates'][1],
            adults=data['adults'], children=data['children'],
            results_size=result_size, sort_method=sort_method,
            file_name=json_file_name, not_debug=False
        )
        # site_api.show_hotels(hotels)
        return hotels
    return []


def distance_to_km(distance: str, unit: str) -> str:
    """
        Если единица измерения мили, то переводит мили в километры иначе оставляет те же значения.
        :param
        distance: значение в милях или км.
        unit: единица измерения.
        :return: форматированная строка - километры.
    """
    mile_km = 1.60934
    if distance and unit == "MILE":
        return f"{float(distance) * mile_km: .2f} km"
    return f"{distance: .2f} {unit.lower()}"


def make_hotels_menu(hotels: list = None) -> str:
    """
    Создает сообщение/меню с номерами отелей для выбора пользователем номера нужного отеля.
    :param hotels: Список отелей полученных из API hotels.com
    :return: текст для создания сообщения со списком отелей и их номеров в меню.
    """
    out_text = ""
    char_non_spacer = "\u00A0"
    if hotels:
        out = [
            f"<b>{i + 1}</b>.\t{hotel_i['name']} {hotel_i['price']: .2f} {hotel_i['currency'].lower()} {distance_to_km(hotel_i['dist'], hotel_i['unit'])}"
            for i, hotel_i in enumerate(hotels)
        ]
        out_text = "\n".join(out)
    else:
        out_text = LEXICON['no_find_hotels']
    return out_text


async def process_children_sent(message: types.Message, state: FSMContext):
    """
    Хэндлер сработает, если введены цифры.
    Проверяет корректный возраст детей.
    Сохраняет их в целочисленный список в словарь data с ключом 'children'.
    Создает меню для выбора отеля и выводит клавиатуру для сортировки этого меню.
    Переводит машину состояний в состояние ожидания ввода выбора отеля 'fill_hotel'.
    """
    check_result, children = check_children_string(message.text)
    if check_result:
        async with state.proxy() as data:
            data['children'] = children
            await delete_swear_message_chat(data)
            await bot_delete_message(
                chat_id=data['invitation_message'].chat.id,
                message_id=data['invitation_message'].message_id
            )
            children_info = make_children_string(children)
            if children_info:
                await message.answer(text=f"{children_info}\n{LEXICON['wait']}")
            else:
                await message.answer(text=f"{LEXICON['wait']}")
            hotels = await request_hotel_data(message.from_user.id, data, SORT_LIST[0])
            if hotels:
                data['hotels_list'] = hotels
                data['invitation_message'] = await message.answer(
                    text=f"{LEXICON['choice_hotels']}\n{make_hotels_menu(data['hotels_list'])}\n\n"
                         f"{LEXICON['sort_hotels']} <b>{SORT_LIST[0]}</b>",
                    reply_markup=inline_keyboards.sort_keyboard()
                )
                await FSMRequestForm.fill_hotel.set()
            else:
                await message.answer(text=LEXICON['no_find_hotels'])
        await message.delete()
    else:
        await warning_not_children(message, state, children)
        await FSMRequestForm.fill_children.set()


async def warning_not_children(message: types.Message, state: FSMContext, broken_ages: List[int] = None):
    """  Хэндлер сработает, если во время ввода возраста детей будет введено что-то некорректное"""
    async with state.proxy() as data:
        broken_message = "" if broken_ages is None else ', '.join([f'{age_i}' for age_i in broken_ages])
        swear_word = LEXICON['swear_word'] if await delete_swear_message_chat(data) else ""
        data['swear_message'] = await message.answer(
            text=f"{swear_word}{LEXICON['bad_list_children']}{broken_message}\n"
                 f"{LEXICON['input_children']}{LEXICON['wrong_children']}{LEXICON['/cancel']}")
    await message.delete()
    await FSMRequestForm.fill_children.set()


def request_hotel_summary(data: FSMContextProxy) -> list:
    """
    Получает с API Hotels.com подробную информацию об отеле.
    :param data: Машина состояний.
    :return: Список данных об отеле.
    """
    region_id = data['region_info'].get('id', "") if 'region_info' in data else ""
    region_name = data.get('region_name', "")
    hotel_id = data['hotel'].get('id', "") if 'hotel' in data else ""
    json_file_name = create_file_name(hotel_id, region_id, region_name, relative_position=".") if USE_TMP_FILE else None
    if hotel_id:
        hotels_summary = site_api.get_summary_list(look_hotel_id=hotel_id, file_name=json_file_name, not_debug=False)
        # site_api.show_summary(hotels_summary)
        return hotels_summary
    return []


async def hotel_index_choice(message: types.Message, state: FSMContext):
    """
        Хэндлер сработает, если введен корректный индекс отеля из меню.
        Проверяет полученное число/индекс меню, оно должно быть 'внутри' меню.
        Удаляет ненужные данные из словаря data. Сохраняет данные из меню в 'hotel'.
        Получает подробные данные об отеле из API Hotels.com и сохраняет их.
        Останавливает машину состояний. Записывает все полученные данные в БД по id пользователя
        Выводит сообщение с полученными данными об отеле и предлагает смотреть фотографии отеля
    """
    hotel_index = int(message.text.strip())
    async with state.proxy() as data:
        len_hotels = len(data['hotels_list'])
    if 1 <= hotel_index <= len_hotels:
        async with state.proxy() as data:
            data['hotel'] = data['hotels_list'][hotel_index - 1]
            await bot_delete_message(
                chat_id=data['invitation_message'].chat.id,
                message_id=data['invitation_message'].message_id
            )
            data.pop('hotels_list', None)
            data.pop('invitation_message', None)
            await delete_swear_message_chat(data)
            data.pop('swear_message', None)
            await message.answer(text=f"{LEXICON['final_hotel']} <b>{data['hotel']['name']}</b>\n{LEXICON['wait']}")

            summary_info = request_hotel_summary(data)

            if summary_info:
                data['hotel_info'], data['hotel_url'] = summary_info[:2]
            else:
                data['hotel_info'], data['hotel_url'] = None, None

        results_data = await state.get_data()

        if online_user_db.get(message.from_user.id, None) is None:
            await constants_set(message.from_user.id)
        user_config = online_user_db.get(message.from_user.id, None)
        if user_config:
            user_config.last_query_data = results_data

        storage = UsersActions()
        storage.add_user_data(
            user_id=message.from_user.id,
            date_time=time.time(),
            user_name=message.from_user.first_name,
            chat_id=message.chat.id,
            user_data=results_data)
        # storage.inform_db()
        await state.finish()
        await message.delete()

        await showdata_command(message)
    else:
        await warning_not_hotel_index(message, state)
        await FSMRequestForm.fill_hotel.set()


async def warning_not_hotel_index(message: types.Message, state: FSMContext):
    """  Хэндлер сработает, если во время ввода индекса отеля будет введено что-то некорректное"""
    async with state.proxy() as data:
        len_menu = len(data['hotels_list'])
        swear_word = LEXICON['swear_word'] if await delete_swear_message_chat(data) else ""
        data['swear_message'] = await message.answer(
            text=f"{swear_word}{LEXICON['wrong_hotel_index']} {len_menu}{LEXICON['/cancel']}"
        )
    await message.delete()
    await FSMRequestForm.fill_hotel.set()


async def hotels_sort(message: types.Message, state: FSMContext):
    """
        Хэндлер сработает на команды "lowprice", "highprice", "bestdeal".
        Сортирует список отелей и выводит новое меню выбора отеля.
        В меню добавляет информацию о текущем методе сортировки.
     """
    async with state.proxy() as data:
        if data['hotels_list']:
            sort_method = message.text[1:] if message.text[1:] in SORT_LIST else None
            if sort_method:
                site_api.sort_hotel_list(data['hotels_list'], sort_method)
                menu_message: types.Message = data['invitation_message']
                await bot_edit_message(
                    chat_id=menu_message.chat.id, message_id=menu_message.message_id,
                    text=f"{LEXICON['choice_hotels']}\n{make_hotels_menu(data['hotels_list'])}\n\n"
                         f"{LEXICON['sort_hotels']} <b>{sort_method}</b>",
                    reply_markup=inline_keyboards.sort_keyboard()
                )
            await FSMRequestForm.fill_hotel.set()
        else:
            await message.answer(text='список отелей пуст, сортировать нечего')
    await message.delete()


async def hotels_sort_buttons(callback: types.CallbackQuery, state: FSMContext):
    """
    Хэндлер сработает по нажатию на кнопки сортировки "lowprice", "highprice", "bestdeal".
    Сортирует список отелей и выводит новое меню выбора отеля.
    В меню добавляет информацию о текущем методе сортировки
    """
    async with state.proxy() as data:
        if data['hotels_list']:
            sort_method = callback.data if callback.data in SORT_LIST else None
            if sort_method:
                site_api.sort_hotel_list(data['hotels_list'], sort_method)
                menu_message: types.Message = data['invitation_message']
                await bot_edit_message(
                    chat_id=menu_message.chat.id, message_id=menu_message.message_id,
                    text=f"{LEXICON['choice_hotels']}\n{make_hotels_menu(data['hotels_list'])}\n\n"
                         f"{LEXICON['sort_hotels']} <b>{sort_method}</b>",
                    reply_markup=inline_keyboards.sort_keyboard()
                )
            await FSMRequestForm.fill_hotel.set()
        else:
            await callback.message.answer(text='список отелей пуст, сортировать нечего')


async def cancel_command(message: types.Message, state: FSMContext):
    """ Хэндлер сработает на команду '/cancel' и отключит машину состояний"""

    current_state = await state.get_state()
    if current_state is None:
        await message.answer(text=LEXICON['not_in_cancel'])
        return
    async with state.proxy() as data:
        data.clear()
    await state.reset_state()

    if online_user_db.get(message.from_user.id, None) is None:
        await constants_set(message.from_user.id)
    user_config = online_user_db.get(message.from_user.id, None)
    if user_config:
        user_config.last_query_data.clear()

    await message.answer(text=LEXICON['info_cancel'])


async def showdata_command(message: types.Message):
    """
    Хэндлер сработает на команду /showdata и отправит в чат данные об отеле записанные в БД.
    """
    user_config = online_user_db.get(message.from_user.id, None)
    if user_config:
        if user_config.last_query_data:
            info_user = user_config.last_query_data

            children_info = make_children_string(info_user["children"])
            hotel = info_user['hotel']
            hotel_info = info_user['hotel_info']
            region = info_user['region_info']
            country = info_user['region_info']['country_name']
            stars = hotel_info.get('stars', '')
            coordinates = info_user['hotel_info'].get('location', None)
            if coordinates:
                out_coordinates = f"{coordinates[0]}, {coordinates[1]}"
                link_coordinates = f"<a href='https://maps.google.com/maps?q={coordinates[0]},{coordinates[1]}'>google map</a>"
            else:
                out_coordinates, link_coordinates = "", ""
            coordinates = info_user['hotel_info']['location'] if info_user['hotel_info']['location'] else ""

            check_in_date = parse(info_user["dates"][0], dayfirst=True)
            check_out_date = parse(info_user["dates"][1], dayfirst=True)
            days_numb = abs(relativedelta(check_out_date, check_in_date).days) + 1

            char_star = "\u2B50"
            char_new_line = "\n"
            stars_line: str = f"{char_star * round(stars)}" if stars else ""
            hotel_info_line = f" <b>{hotel_info['name']}</b>\t{stars_line}\n{hotel_info['address']}, {country}\n" \
                             f"<b>{hotel['price']: .2f} {hotel['currency'].lower()}</b> ночь, " \
                             f"{days_numb * hotel['price']: .2f} всего\n" \
                             f"до центра: {distance_to_km(hotel['dist'], hotel['unit'])}\n" \
                             f"координаты: {out_coordinates}\n" \
                             f"{link_coordinates}"

            text_message = f"отель: {hotel_info_line}\n" \
                           f"даты: <b>{info_user['dates'][0]}, {info_user['dates'][1]}</b>\n" \
                           f"ночей: <b>{days_numb}</b>\n" \
                           f"взрослых: <b>{info_user['adults']}</b>\n" \
                           f"{children_info}{char_new_line if children_info else ''}" \
                           f"место: {region['name']}, {region['type'].lower()}"

            await message.answer(text=text_message)
            hotel_map = hotel_info.get('map_url', None)
            if hotel_map:
                await message.answer_photo(photo=hotel_info['map_url'], caption=f"map")
            hotel_urls = info_user.get('hotel_url', None)
            len_hotel_url = len(hotel_urls) if hotel_urls else 0
            if user_config.IMAGE_SIZE < len_hotel_url:
                len_hotel_url = user_config.IMAGE_SIZE
            if len_hotel_url:
                await message.answer(
                    text=f"{LEXICON['/showimage']} "
                         f"{LEXICON['image_quantity'](len_hotel_url)}\n"
                         f"{LEXICON['push-button']}",
                    reply_markup=inline_keyboards.show_image_keyboard(len_hotel_url))
            await message.answer(text=LEXICON['finish'])
        else:
            await message.answer(text=LEXICON['wrong_showdata'])
    else:
        await message.answer(text=LEXICON['wrong_showdata'])


async def get_image_list(user_id: int, args: List[str]) -> Union[List[types.InputMediaPhoto], None]:
    """
    Формирует список объектов изображений из БД
    :param user_id:
    :param args:
    :return:
    """

    if online_user_db.get(user_id, None) is None:
        await constants_set(user_id)
    user_config = online_user_db.get(user_id, None)

    if len(args) > 1 and args[1].isdigit():
        required_number_images = int(args[1])
    else:
        required_number_images = user_config.IMAGE_SIZE
    info_user = user_config.last_query_data

    if info_user.get('hotel_url', ''):
        hotel_name = info_user['hotel_info']['name']
        len_hotel_url = len(info_user['hotel_url'])
        image_max = user_config.IMAGE_SIZE if len_hotel_url >= user_config.IMAGE_SIZE else len_hotel_url
        if 0 < required_number_images <= image_max:
            image_max = required_number_images
        urls = [
            InputMediaPhoto(media=photo_i, caption=f"{number_i + 1}. {hotel_name}")
            for number_i, photo_i in enumerate(info_user['hotel_url'][:image_max])
        ]
        return urls
    return None


async def show_image_callback(callback: types.CallbackQuery):
    """
    Хэндлер сработает по нажатию на кнопку с нужным количеством изображений.
    Получит список изображений из БД, создаст группу изображений и отправит ее в чат.
    """
    user_config = online_user_db.get(callback.from_user.id, None)

    if user_config:
        urls = await get_image_list(callback.from_user.id, callback.data.split())
        if urls:
            await callback.message.answer_media_group(media=urls)
        else:
            await callback.answer(text=LEXICON['wrong_show_image'])
    else:
        await callback.answer(text=LEXICON['wrong_showdata'])


async def show_image_command(message: types.Message):
    """
    Хэндлер сработает на команду /showimage.
    Если есть параметр, то получит список изображений из БД,
    создаст группу изображений и отправит ее в чат.
    """
    user_config = online_user_db.get(message.from_user.id, None)
    if user_config:
        urls = await get_image_list(message.from_user.id, message.text.split())
        if urls:
            await message.answer_media_group(media=urls)
        else:
            await message.answer(text=LEXICON['wrong_show_image'])
    else:
        await message.answer(text=LEXICON['wrong_showdata'])


def hotel_line(hotel_row) -> Union[str, None]:
    """
    Формирует текстовую строку информации об отеле для отображения истории запросов
    """
    if hotel_row:
        query_info: dict = json.loads(hotel_row[5])
        hotel_info = query_info['hotel_info']
        hotel = query_info['hotel']
        time_info = datetime.fromtimestamp(hotel_row[2]).strftime('%d.%m.%Y, %H:%M')
        return f"{time_info} <b>{hotel_info['name']}</b>, {hotel_info['address']}, {hotel_info['country']}, <b>{round(hotel['price'], 2)}</b> {hotel['currency']}"
    return None


async def get_history_info(user_id: int) -> Union[str, None]:
    """
    Формирует текст сообщения с историей запросов
    """
    user_config = online_user_db.get(user_id, None)
    if user_config:
        story_size = user_config.STORY_SIZE
    else:
        story_size = MAX_STORY_SIZE

    storage = UsersActions()
    user_history = storage.get_user_sortingtime_limit(user_id, story_size)
    if user_history:
        s1 = [f"<b>{index + 1}</b>. {hotel_line(row_i)}" for index, row_i in enumerate(user_history)]
        return "\n".join(s1)
    return None


async def history_command(message: types.Message, state: FSMContext):
    """
    Хэндлер сработает на команду '/history' и покажет историю запросов.
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(text=LEXICON['history_command'])
        user_history = await get_history_info(message.from_user.id)
        if user_history:
            await message.answer(text=user_history)
        else:
            await message.answer(text=LEXICON['history_empty'])
    else:
        await message.answer(text=LEXICON['wrong_history'] + LEXICON['/cancel'])

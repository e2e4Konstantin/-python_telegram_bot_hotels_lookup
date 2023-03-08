from typing import Callable, Union, Dict
import os
from dataclasses import dataclass

from dotenv import load_dotenv, find_dotenv

"""
Здесь собраны все константы
"""

load_dotenv(find_dotenv(raise_error_if_not_found=True))
HOTELS_API_KEY = os.getenv("API_KEY", None)
BOT_TOKEN = os.getenv("BOT_TOKEN", None)

""" для сокращения обращений к серверу Hotels.com, использовать запись ответов сервера в файлы """
USE_TMP_FILE = True

MAX_IMAGE_SIZE: int = 10  # максимальное количество результатов в запросе изображений отеля
                          # Media group must include 2-10 items
MAX_RESULT_SIZE: int = 10  # максимальное количество результатов в запросе поиска отелей
MAX_STORY_SIZE: int = 10  # максимальное количество результатов в выдаче истории запросов

MAX_ADULTS = 4  # максимальное число взрослых путешественников
MAX_CHILDREN = 4  # максимальное число детей
MAX_DAYS = 30  # максимальное количество запрашиваемых дней проживания
MIN_AGE_CHILD = 1  # минимальный возраст детей
MAX_AGE_CHILD = 10  # максимальный возраст детей


@dataclass
class UsersConstants:
    """
    В экземплярах этого класса храниться конфигурация для каждого пользователя
    """
    IMAGE_SIZE: int = 7
    RESULT_SIZE: int = 10
    STORY_SIZE: int = 9
    last_query_data: dict = None


""" хранилище для последней сессии/поиска """
online_user_db: dict = {int: UsersConstants}

RE_DATE = r"(?:[0-9]{1,2}[-|/|.]){2}[0-9]{2,4}"
RE_DIGITS = r"(\d+)"
RE_NAME_REGION = r"[A-Za-zА-Яа-я— -]"  # только буквы тире длинное тире и пробел

REGION_TYPE_FILTER = ["CITY", "AIRPORT", "NEIGHBORHOOD"]  # фильтр регионов
RUS_REGION_TRANS = ["город", "аэропорт", "район"]
TRANSLATE_REGION_DICT = dict(zip(REGION_TYPE_FILTER, RUS_REGION_TRANS))

SORT_LIST = ("lowprice", "highprice", "bestdeal")

LEXICON: Dict[str, Union[str, Callable]] = {
    '/start': "привет. Я бот для поиска отеля.\n",
    '/help_command': "<b>/start</b>\t\tперезапуск бота\n"
                     "<b>/cancel</b>\t\tпрервать поиск\n"
                     "<b>/fillform</b>\tначать поиск\n"
                     "<b>/config</b>\t\tустановки\n",

    '/help_info': "Введи команду <b>/fillform</b>, "
                  "потом название города или региона, где ищешь отель. "
                  "Если я найду такое место, то выбери из предложенных вариантов. Дальше уже не заблудишься.",

    'finish': "Поиск завершен. Найди другой отель, введи команду <b>/fillform</b>.",

    '/config': "Установлены параметры:\n\n",

    'config_image': "фотографий в выдаче:",
    'config_hotels': "отелей в выдаче:",
    'config_history': "результатов в истории:",
    'config_setting': "если хочешь изменить набери /customising",

    '/customising': "Введи три числа через запятую или пробел:\n",

    'info_constant': f"  фотографий от 1 до {MAX_IMAGE_SIZE},\n"
                     f"  отелей от 1 до {MAX_RESULT_SIZE}\n"
                     f"  глубину истории от 1 до {MAX_STORY_SIZE}.\n"
                     f"  <em>например:</em>  <code>4, 9, 5</code> или  <code>8 10 7</code>"
    ,
    'wrong_constant': f"Надо ввести <b>3</b> числа,\nсколько хочешь получить результатов:\n",

    '/fillform': "Веди название города или региона, например:\n"
                 "<code>Manchester</code>, <code>Berlin</code>, <code>Milan</code>, <code>New York</code>",

    '/cancel': "\n\n<em>Если хочешь прервать поиск - отправь команду /cancel</em>",
    'not_in_cancel': "Ты еще не заполнял запрос. \nДля заполнения - отправь команду /fillform",
    'info_cancel': "Ты вышел из заполнения запроса\nЧтобы снова перейти к заполнению запроса - "
                   "отправь команду /fillform",
    '/showdata': "Чтобы посмотреть данные отправь команду /showdata",
    'wrong_showdata': "Ты еще не заполнял данные для запроса.\nДля заполнения - отправь команду /fillform",
    '/showimage': "Чтобы посмотреть фотографии отправь команду "
                  "<code>/showimage 3</code>, где 3 количество фотографий, "
                  "если без параметра, то увидишь все доступные.",

    'push-button': "Лень набирать команду, нажми кнопку с нужным количеством.",
    'image_quantity': lambda x: f"Всего есть <b>{x}</b> фотографий.",

    'wait': "<em>подожди немного</em>",
    'look_region': "Ищу варианты регионов:",
    'choice_region': "Выбери из списка <b>номер</b> региона который тебе нужен:\n",
    'wrong_region': "не похоже на название региона.\n"
                    "Используй только буквы, дефис и пробел.\n"
                    "Пожалуйста, введи название региона, например: 'milan', 'Manchester'...  ",
    'wrong_number_region': "При выборе региона используй только цифры от 1 до",
    'final_region': "Выбрано место:\n",
    'no_find_region': "Не могу найти такой регион. Попробуй еще.",

    'input_dates': "Введи дату заезда и отъезда:\n"
                   "например так:\n",
    'wrong_dates': f"при вводе дат что-то не то\n"
                   f"нужно ввести 2 даты, заезда и отъезда\n день/месяц/год\n"
                   f"используй разделители в дате: (. / -)\n"
                   f"например 2-2-2023 12-02-23\n"
                   f"дата заезда должна быть меньше даты отъезда максимум на {MAX_DAYS} дней:\n"
                   f"попробуй еще раз: ",
    'result_dates': "выбраны даты:\n",
    'check_in_date': "дата заезда:",
    'check_out_date': "дата отъезда:",

    'input_adults': "введи количество взрослых:",
    'wrong_adults': f"Пожалуйста, введи число от 1 до {MAX_ADULTS}.",
    'result_adults': "взрослых:",

    'input_children': f"введи возраст детей "
                      f"от {MIN_AGE_CHILD} до {MAX_AGE_CHILD} лет через запятую или пробел,\n"
                      f"например, с вами два ребенка 3 и 12 лет, введи: 3, 12\nесли детей нет, отправь: 0\n",
    'wrong_children': "используй любой разделитель, если один ребенок 7 лет, введи: 7",
    'bad_list_children': f"это неправильно: ",

    'look_hotels': "ищу отели в регионе: ",
    'choice_hotels': "Выбери из списка <b>номер</b> отеля который тебе нужен:\n"
                     "(<em>название, цена, расстояние от центра</em>)\n",
    'sort_hotels': f"сортировка:",
    'no_find_hotels': "Не могу найти отели по твоему запросу. Попробуй другие параметры.",
    'wrong_hotel_index': "При выборе отеля используй его номер, цифры от 1 до",
    'zero_hotel_list': "список отелей пуст, сортировать нечего",
    'final_hotel': "Выбран отель:\n",

    'wrong_show_image': "Нет доступных фотографий.",

    'data_saved': "Спасибо! Данные сохранены!",
    'swear_word': "я тебе уже писал:\n",
    'other_answer': "Извини, мне непонятно...",
    'history_command': "История запросов:\n",
    'history_empty': "У тебя еще нет истории.",
    'wrong_history': "Заверши текущий поиск отеля, потом набери команду /history"
}

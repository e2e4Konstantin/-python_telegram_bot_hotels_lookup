from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from constants import SORT_LIST
from typing import Union


def sort_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для сортировки списка отелей.
    :return: инлайн клавиатуру
    """
    buttons = [
        [InlineKeyboardButton(text=sort_method_i, callback_data=sort_method_i, resize_keyboard=True)
         for sort_method_i in SORT_LIST]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def show_image_keyboard(len_hotel_url: int = 0) -> Union[InlineKeyboardMarkup, None]:
    """
    Создает клавиатуру для просмотра фотографий отелей.
    Смотреть все, 1/3 фотографии, 1/3 фотографий.
    :param len_hotel_url: максимальное количество фотографий для просмотра.
    :return: инлайн клавиатуру
    """
    if len_hotel_url > 0:
        if len_hotel_url <= 3:
            button_data = [(f"{len_hotel_url}", f"show_image {len_hotel_url}")]
        else:
            button_data = [(f"{len_hotel_url}", f"show_image {len_hotel_url}")]
            text_2 = len_hotel_url // 2 - 1
            text_3 = len_hotel_url - len_hotel_url // 2

            button_data.append((f"{text_3}", f"show_image {text_3}"))
            button_data.append((f"{text_2}", f"show_image {text_2}"))

        buttons = [
            [InlineKeyboardButton(text=buttons_i[0], callback_data=buttons_i[1], resize_keyboard=True)
             for buttons_i in button_data
             ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    return None

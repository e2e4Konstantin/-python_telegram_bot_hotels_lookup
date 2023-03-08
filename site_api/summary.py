from settingsAPI import api_setting, str_no_space, create_file_name
from constants import MAX_IMAGE_SIZE
from init_site_api import SiteApi
from requests import request
from typing import Any
import os
from PIL import Image
from typing import Union, List


def summary_json_parse(json_link: Any) -> Union[List, None]:
    """
        Разбирает ответ сервера Hotels.com на запрос информации об отеле.
        :param json_link: Ссылка данные об отеле полученные
                          из запроса к серверу в json формате
                          количество ссылок на фотографии, ограничено константой конфигурации MAX_IMAGE_SIZE
        :return: Список подробностей отеля
    """
    if json_link and json_link.get('data').get('propertyInfo').get('summary'):
        summary = [{}, []]
        info = json_link['data']['propertyInfo']['summary']
        coordinates = info['location']['coordinates']
        summary[0] = {"id": info['id'],
                           "name": info['name'],
                           "address": info['location']['address']['addressLine'],
                           "country": info['location']['address']['countryCode'],
                           "location": (coordinates['latitude'], coordinates['longitude']),
                           }
        stars = info.get('overview').get('propertyRating')
        summary[0]["stars"] = stars.get('rating', None) if stars else None

        images = json_link['data']['propertyInfo']['propertyGallery']['images']
        summary[1] = [image_i['image']['url'] for image_i in images][:MAX_IMAGE_SIZE]

        location = json_link['data']['propertyInfo']['summary'].get('location', None)
        map_url = location.get('staticImage', None) if location else None
        summary[0]['map_url'] = map_url.get('url', None) if map_url else None
        return summary
    return None


def get_summary_list(look_hotel_id: str = "", file_name: str = "", not_debug: bool = True) -> Union[List, None]:
    """
        Формирует запрос на сервер Hotels.com для получения информации об отеле.
        Полученный ответ разбирает на список с нужными данными.
        :param look_hotel_id: Id отеля
        :param file_name: имя файла, в который запишется ответ
                          или данные прочитаются из этого файла если ранее такой запрос уже был.
        :param not_debug: Вывод в консоль отладочных сообщений.
        :return: Список регионов.
    """
    summary_out = None
    look_hotel_id = str_no_space(look_hotel_id)
    if not look_hotel_id or not look_hotel_id.isdigit():
        return None
    else:
        api_setting.set_property_id(property_id=look_hotel_id)
        summary = SiteApi(**api_setting.summary.url)
        summary.get_smart_data(api_setting.summary.query, file_name, not_debug=not_debug)
        if summary.status:
            summary_out = summary_json_parse(summary.json_encoders)
    return summary_out


def show_image_file(link_file: str) -> None:
    """ Показывает изображение по ссылке """
    img = Image.open(link_file)
    img.show()


def show_image_url(image_url: str, file_to: str) -> None:
    """ Показывает изображение по url и записывает его в указанный файл """
    img_link = request("GET", image_url, stream=True)
    if img_link.status_code == 200:
        img = Image.open(img_link.raw)
        img.save(file_to)
        img.show()


def show_image(image_url: str = "", dir_position: str = "..") -> None:
    """
    Выводит в консоль изображение по url.
    Если такое изображение уже имеется в папке "hotels_images", то покажет из папки,
    если нет, то показывает по url.
    :param image_url: Url изображения
    :param dir_position: маршрут к папке "hotels_images"
    :return: None
    """
    name_img = os.path.basename(image_url).split("?")[0]
    link_file = os.path.join(dir_position, "hotels_images", name_img)
    if name_img and os.path.exists(link_file):
        show_image_file(link_file)
    else:
        show_image_url(image_url, link_file)


def show_images_list(summary: list = None, foto_limit: int = 1, dir_position: str = "..") -> None:
    """
    Выводит в консоль изображения отеля url которых содержится в списке
    """
    print("Изображения отеля:")
    if summary:
        [show_image(img_i, dir_position) for img_i in summary[:foto_limit]]
    else:
        print("\nизображения отеля не найдены")


def show_summary(summary: list) -> None:
    """
        Выводит в консоль подробности отеля
        :param summary: список с подробностями
        :return: None
    """
    print("Подробности отеля:")
    if summary:
        stars = summary[0].get('stars', '')
        char_star = f"{'* ' if stars else ''}"
        print(f"id: {summary[0]['id']} {stars}{char_star}{summary[0]['name']}, "
              f"{summary[0]['address']} {summary[0]['country']} {summary[0]['location']}")
        [print(f"\t{x}") for x in summary[1]]
    else:
        print("\n\tподробности отеля не найдены")


if __name__ == '__main__':
    print("-- Summary --")
    region = 'Munchen'
    region_id = "2452"

    hotel_id = "29500975"
    json_file_name = create_file_name(hotel_id, region_id, region, relative_position="..")

    summary_info = get_summary_list(
        look_hotel_id=hotel_id,
        file_name=json_file_name, not_debug=False
    )
    show_summary(summary_info)
    show_images_list(summary_info[1], 2, "..")

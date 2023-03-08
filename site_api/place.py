from typing import Union
from settingsAPI import api_setting, str_clearing, create_file_name
from init_site_api import SiteApi

from typing import Any

from constants import REGION_TYPE_FILTER


def place_json_parse(json_link: Any) -> Union[list, None]:
    """
    Разбирает ответ сервера Hotels.com на запрос доступных регионов.
    Оставляет только те регионы типы которых содержатся в списке REGION_TYPE_FILTER.
    :param json_link: Ссылка на данные о регионах полученные
                      из запроса к серверу в json формате
    :return: Список регионов
    """
    if json_link:
        places = []
        success = json_link.get('rc', False)
        if success and success == "OK":
            places = [{
                'id': x.get('gaiaId', ""),
                'type': x.get('type', ""),
                'a3_code': x['hierarchyInfo']['country']['isoCode3'],
                'country_name': x['hierarchyInfo']['country']['name'],
                'name': x['regionNames']['fullName']
            } for x in json_link['sr'] if x.get('gaiaId', False) and x.get('type', "") in REGION_TYPE_FILTER]
        return places
    return None


def get_places_list(target_place: str = "", file_name: str = "", not_debug: bool = True) -> Union[list, None]:
    """
    Формирует запрос на сервер Hotels.com для получения доступных регионов, посылает его на сервер.
    Полученный ответ разбирает на список регионов.
    :param target_place: Название искомого региона
    :param file_name: имя файла, в который запишется ответ
                      или данные прочитаются из этого файла если ранее такой запрос уже был.
    :param not_debug: Вывод в консоль отладочных сообщений.
    :return: Список регионов.
    """
    places_out = None
    target_place = str_clearing(target_place)
    if not target_place:
        return None
    else:
        api_setting.set_target_place(target_place)
        place = SiteApi(**api_setting.place.url)

        place.get_smart_data(api_setting.place.query, file_name, not_debug=not_debug)
        if place.status and place.json_encoders.get('rc', False) == 'OK':
            places_out = place_json_parse(place.json_encoders)
    return places_out


def show_places(places: list = None) -> None:
    """
    Выводит в консоль список регионов
    :param places: список регионов
    :return: None
    """
    print("Список регионов:")
    if places:
        [
            print(
                number, f"{region_i['id'][:8]: >9} "
                        f"{region_i['type'].lower(): <14} "
                        f"{region_i['country_name']} "
                        f"{region_i['a3_code']} "
                        f"{region_i['name']}"
            )
            for number, region_i in enumerate(places)
        ]
    else:
        print("\n\tСписок регионов пуст.")


if __name__ == '__main__':
    print("-- Regions --")
    region = 'Munchen'
    json_file_name = create_file_name(region, relative_position="..")
    regions = get_places_list(target_place=region, file_name=json_file_name, not_debug=False)
    show_places(regions)

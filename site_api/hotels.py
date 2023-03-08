from settingsAPI import api_setting, str_no_space, create_file_name
from init_site_api import SiteApi

from typing import Any, Union, List
from constants import MAX_RESULT_SIZE


def sort_hotel_list(src: list, methods: str = "lowprice") -> None:
    """
    Сортирует список отелей в соответствии с указанным методом
    :param src: Список отелей
    :param methods: Метод сортировки. По возрастанию цены, по убыванию цены,
    по интегральному показателю минимальное расстояние от цента + минимальная цена
    :return: None
    """
    if methods == "lowprice":
        sort_func = lambda x: x['price']
    elif methods == "highprice":
        sort_func = lambda x: -x['price']
    elif methods == "bestdeal":
        sort_func = lambda x: x['bestdeal']
    else:
        sort_func = lambda x: (x['price'], x['dist'])
    src.sort(key=sort_func, reverse=False)


def offer_json_parse(json_link: Any, sort_method: str = "lowprice") -> Union[List, None]:
    """
        Создает список отелей отсортированный в соответствии с указанным методом.
        Разбирает ответ сервера Hotels.com
        Для каждого отеля создается значение 'bestdeal в котором вычисляется показатель -
        минимальное расстояние от цента + минимальная цена.
        :param json_link: Ссылка данные об отелях полученные из запроса к серверу в json формате
        :param sort_method: Метод сортировки
        :return: Список отелей
        """
    if json_link:
        search_result = json_link.get('data', None).get('propertySearch', None).get('properties', None)
        if search_result and len(search_result) > 0:
            hotels_offer = []
            for hotel_i in search_result:
                distance = hotel_i.get('destinationInfo').get('distanceFromDestination', None) if hotel_i.get('destinationInfo', None) else None
                price = hotel_i.get('price').get('lead', None) if hotel_i.get('price', None) else None
                currency_info = hotel_i.get('price').get('lead').get('currencyInfo', None) if hotel_i.get('price', None) and hotel_i.get('price').get('lead', None) else None
                hotel_image = hotel_i.get('propertyImage').get('image', None) if hotel_i.get('propertyImage', None) else None

                hotels_offer.append({
                    'id': hotel_i.get('id', ''),
                    'name': hotel_i.get('name', ''),
                    'dist': distance.get('value', 0) if distance else 0,
                    'unit': distance.get('unit', '') if distance else '',
                    'price': price.get('amount', 0) if price else 0,
                    'currency': currency_info.get('code', '') if currency_info else '',
                    'image': hotel_image. get('url', '') if hotel_image else ''
                })
            if hotels_offer:
                min_price = min(hotels_offer, key=lambda x: x['price'])['price']
                min_dist = min(hotels_offer, key=lambda x: x['dist'])['dist']
                [x.update({'bestdeal': round(abs(x['price'] - min_price) + abs(x['dist'] - min_dist), 2)}) for x in hotels_offer]
                sort_hotel_list(hotels_offer, sort_method)
                return hotels_offer
    return None



def get_hotels_list(region_id: str, in_date: str, out_date: str,
                    adults: int, children: List[int], results_size: int = 5,
                    sort_method: str = "lowprice",
                    file_name: str = "", not_debug: bool = True) -> Union[List, None]:
    """
    Формирует запрос на сервер Hotels.com для получения предложения отелей, посылает его на сервер.
    Полученный ответ разбирает на список отелей.
    :param region_id:   Id региона, в котором ищем отели.
    :param in_date:     Дата заезда
    :param out_date:    Дата выезда
    :param adults:      Количество взрослых
    :param children:    Список возрастов детей
    :param results_size: Количество пунктов в ответе
    :param sort_method: Метод сортировки списка отелей
    :param file_name:   Имя файла в который записываем ответ сервера или читаем
                        в него если такой файл уже записан
    :param not_debug:   Вывод в консоль отладочных сообщений
    :return:            Список отелей
    """
    offers = None
    region_id = str_no_space(region_id)
    if not region_id or not region_id.isdigit():
        return None
    else:
        api_setting.set_target_destination(region_id)
        api_setting.set_dates(in_date, out_date)
        if len(children) > 0:
            api_setting.set_guests_numbers(adults, children)
        else:
            api_setting.set_guests_numbers(adults)
        api_setting.set_results_size(results_size)

        offer = SiteApi(**api_setting.offer.url)
        offer.get_smart_data(api_setting.offer.query, file_name, not_debug=not_debug)
        if offer.status:
            offers = offer_json_parse(offer.json_encoders, sort_method)
    return offers


def show_hotels(hotels: list = None) -> None:
    """
        Выводит в консоль список отелей
        :param hotels: список регионов
        :return: None
        """
    print("Список отелей:")
    if hotels:
        [
            print(
                number, f"{hotel_i['id']: >8} {hotel_i['dist']: 6.2f} {hotel_i['unit']} "
                        f"{hotel_i['price']: 6.2f} {hotel_i['currency']} "
                        f"{hotel_i['bestdeal']: 6.2f} {hotel_i['name']}"
            )
            for number, hotel_i in enumerate(hotels)]
    else:
        print("\n\tв списке отелей пусто")


if __name__ == '__main__':
    print("-- Hotels --")
    region = 'Munchen'
    region_id = "2452"
    json_file_name = create_file_name(region_id, region, relative_position="..")
    offer = get_hotels_list(
        region_id=region_id,
        in_date="15/02/2023", out_date="22/02/2023",
        adults=2, children=[2, 7],
        results_size=MAX_RESULT_SIZE, sort_method="lowprice",
        file_name=json_file_name, not_debug=False
    )
    show_hotels(offer)

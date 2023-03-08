from typing import Union, List
from pydantic import BaseModel
from datetime import datetime
import re
import os

from constants import HOTELS_API_KEY, MAX_RESULT_SIZE, MAX_ADULTS, MIN_AGE_CHILD, MAX_AGE_CHILD, MAX_CHILDREN


def create_file_name(*args, relative_position: str = ".") -> Union[str, None]:
    """
    Создает имя фала из полученных аргументов.
    :param args: Строки тела имени файла
    :param relative_position: папка назначения
    :return: имя файла
    """
    if args:
        tmp_args = [str_clearing(arg_i.strip()).replace(" ", "-") for arg_i in args]
        body_file_name = "_".join(tmp_args).lower()
        return os.path.join(relative_position, "json_data", body_file_name + ".json")
    return None


def str_clearing(src_data: str = None) -> Union[str, None]:
    """ Удаляет из строки повторяющиеся пробелы """
    alfa = re.compile(r"\s+")
    src_data = re.sub(alfa, ' ', src_data)
    if len(src_data) > 0:
        return src_data.strip().lower()
    return None


def str_no_space(src_data: str = None) -> Union[str, None]:
    """ Удаляет из строки все пробелы """
    alfa = re.compile(r"\s+")
    src_data = re.sub(alfa, '', src_data)
    if len(src_data) > 0:
        return src_data
    return None


class UnitRequest(BaseModel):
    url: dict = None
    query: dict = None


place_dict = {
    "url": {"tail_url": "/locations/v3/search",
            "method": "GET",
            "query_name": "params"},
    "query": {
        "q": "",
        "locale": "en_US"
    }
}

offer_dict = {
    "url": {
        "tail_url": "/properties/v2/list",
        "method": "POST",
        "content_type": "application/json",
        "query_name": "json"},
    "query": {
        "destination": {"regionId": ""},
        "checkInDate": {"day": 0, "month": 0, "year": 1900},
        "checkOutDate": {"day": 0, "month": 0, "year": 1900},
        "rooms": [{"adults": 0, "children": [{"age": 0}, {"age": 0}]}],
        "resultsStartingIndex": 0,
        "resultsSize": MAX_RESULT_SIZE, "sort": "PRICE_LOW_TO_HIGH",
        "currency": "USD",
        "locale": "en_US",
    }
}

summary_dict = {
    "url": {
        "tail_url": "/properties/v2/get-summary",
        "method": "POST",
        "content_type": "application/json",
        "query_name": "json"
    },
    "query": {
        "propertyId": "",
        "currency": "USD",
        "locale": "en_US"
    }
}


class HotelsAPIsetup(BaseModel):
    """
    Класс для хранения настроек запросов к API Hotels.com.
    Есть три вида запросов:
        -поиск региона, в котором ищется отель,
        -поиск отелей в этом регионе,
        -получение подробностей выбранного отеля.
    Class SiteSettings создан для хранения api_key.
    Class UnitRequest создан для хранения словарей url и query, каждый для своего типа запроса.
    Атрибуты класса HotelsAPIsetup:
        place создается из экземпляра класса UnitRequest, в который грузится словарь place_dict,
        offer создается из экземпляра класса UnitRequest, в который грузится словарь offer_dict,
        summary создается из экземпляра класса UnitRequest, в который грузится словарь summary_dict.
    Например запрос для поиска региона выглядит так:
        url = "https://hotels4.p.rapidapi.com/locations/v3/search"
        querystring = {"q":"new york","locale":"en_US","langid":"1033","siteid":"300000001"}
        headers = {"X-RapidAPI-Key": "f91cdcaae0mshb0b928c5d2d1378p131890jsnf44c73ce30ca",
	               "X-RapidAPI-Host": "hotels4.p.rapidapi.com"}
        response = requests.request("GET", url, headers=headers, params=querystring).



    """
    hotels_api_key = HOTELS_API_KEY
    host_api: str = "hotels4.p.rapidapi.com"
    place: UnitRequest = UnitRequest.parse_obj(place_dict)
    offer: UnitRequest = UnitRequest.parse_obj(offer_dict)
    summary: UnitRequest = UnitRequest.parse_obj(summary_dict)

    def get_headers(self) -> dict:
        """ Формирует словарь для headers """
        # print(self.hotels_api_key)
        return {"X-RapidAPI-Key": self.hotels_api_key, "X-RapidAPI-Host": self.host_api}

    def get_base_url(self) -> str:
        """ Формирует словарь для url """
        return f"https://{self.host_api}"

    def set_results_size(self, size: int = 5) -> None:
        """ Записывает в словарь запроса списка отелей элемент "resultsSize" """
        if 0 < size < MAX_RESULT_SIZE:
            self.offer.query["resultsSize"] = size
        else:
            self.offer.query["resultsSize"] = MAX_RESULT_SIZE

    def set_target_place(self, target_place: str) -> None:
        """ Записывает в словарь запроса поиска региона название региона """
        self.place.query["q"] = target_place

    def set_target_destination(self, target_region_id: str = "") -> None:
        """ Записывает в словарь запроса списка отелей id требуемого региона """
        target_region_id = str_no_space(target_region_id)
        if target_region_id and target_region_id.isdigit():
            self.offer.query["destination"]["regionId"] = target_region_id
        else:
            self.offer.query["destination"]["regionId"] = ""

    def set_dates(self, checkin_date: str = "", checkout_date: str = "") -> None:
        """ Записывает в словарь запроса списка отелей дату заезда и выезда """
        if not checkin_date.strip() or not checkout_date.strip():
            return None
        else:
            try:
                checkin = datetime.strptime(checkin_date, "%d/%m/%Y").date()
                checkout = datetime.strptime(checkout_date, "%d/%m/%Y").date()
                self.offer.query["checkInDate"]["day"] = checkin.day
                self.offer.query["checkInDate"]["month"] = checkin.month
                self.offer.query["checkInDate"]["year"] = checkin.year
                self.offer.query["checkOutDate"]["day"] = checkout.day
                self.offer.query["checkOutDate"]["month"] = checkout.month
                self.offer.query["checkOutDate"]["year"] = checkout.year
            except Exception as err:
                print(err)
        return None

    def set_guests_numbers(self, adults: int = 1, children: Union[List[int], None] = None) -> None:
        """ Записывает в словарь запроса списка отелей количество взрослых жильцов и список возрастов детей """
        if 0 < adults < MAX_ADULTS:
            self.offer.query["rooms"][0]["adults"] = adults
        else:
            self.offer.query["rooms"][0]["adults"] = 1

        if children:
            self.offer.query["rooms"][0]["children"] = [
                                                           {"age": x} for x in children
                                                           if isinstance(x, int) and MIN_AGE_CHILD < x < MAX_AGE_CHILD
                                                       ][:MAX_CHILDREN]
        else:
            self.offer.query["rooms"][0]["children"] = []

    def set_property_id(self, property_id: str = "") -> None:
        """ Записывает в словарь запроса получения информации об отеле id этого отеля """
        property_id = str_no_space(property_id)
        if property_id and property_id.isdigit():
            self.summary.query["propertyId"] = str_no_space(property_id)
        else:
            self.summary.query["propertyId"] = ""


# создаем экземпляр класса с настройками для всех запросов
api_setting = HotelsAPIsetup()

if __name__ == '__main__':

    set = HotelsAPIsetup()
    print(f"base_url = \t\t{set.get_base_url()}")
    print(f"headers = \t\t{set.get_headers()}")

    set.set_target_place("manchester")
    print(f"place.query = \t{set.place.query}")
    print(f"place.url = \t{set.place.url}")

    set.set_target_destination("2205")
    set.set_dates("15/02/2023", "22/02/2023")
    set.set_guests_numbers(adults=2, children=[2, 7])
    set.set_results_size(10)
    print(f"offer.query =\t{set.offer.query}")
    print(f"offer.urly =\t{set.offer.url}")

    set.set_property_id("1383519")
    print(f"summary.query = {set.summary.query}")
    print(f"summary.urly =\t{set.summary.url}")

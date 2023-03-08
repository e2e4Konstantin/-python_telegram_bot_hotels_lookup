from settingsAPI import HotelsAPIsetup
from pydantic import BaseModel
from typing import Any, Dict, Optional, Union
import requests
import json
import os
import time
import random
from pprint import pprint
import sys

# экземпляр класса с параметрами и настройками запросов
site = HotelsAPIsetup()

class SiteApi(BaseModel):
    """
    Класс для создания конкретного запроса к сайту Hotels.com.
    Параметры для запроса берутся из экземпляра класса с настройками site: HotelsAPIsetup
    base_url: общий для всех запросов url
    headers: заголовок запроса
    tail_url: специфическое для каждого запроса окончание url
    method: метод запроса
    content_type: тип контента
    query_name: имя параметра в запросе
    status: статус ответа на запрос
    json_encoders: значение ответа

    current_costs_response: сколько осталось запросов к Hotels.com
    limit_response: лимит на количество запросов Hotels.com из headers

    """
    base_url: str = site.get_base_url()
    headers: Dict[str, str] = site.get_headers()
    tail_url: str = None
    method: str = None
    content_type: Optional[str]
    query_name: str = None
    status: bool = False
    json_encoders: Union[Any, None] = None

    current_costs_response: str = None
    limit_response: str = None

    def __str__(self):
        """ Строковое представление экземпляра класса"""
        return f"url = {self.url}\nheaders = {self.headers}\nmethod = {self.method}\n" \
               f"content_type = {self.content_type}\nquery_name = {self.query_name}"

    @property
    def url(self):
        """ Возвращает полный url"""
        return self.base_url + self.tail_url

    def balance_current_costs_response(self) -> Union[int, None]:
        """
        Возвращает остаток подключений к Hotels.com
        """
        if self.limit_response and self.current_costs_response:
            return int(self.limit_response) - int(self.current_costs_response)
        return None

    def get_requests_limit_balance(self) -> str:
        """
        :return: Строку с состоянием использованных запросов к сайту Hotels.com
        """
        return f"Лимит запросов: {self.limit_response}\n" \
               f"Осталось запросов: {self.current_costs_response}\n" \
               f"Использовано запросов: {self.balance_current_costs_response()}"

    def get_data(self, query_dict: dict, not_debug: bool = True) -> None:
        """
        Формирует все параметры запроса в data_par.
        Посылает запрос. Получает ответ и при удачном исполнении, записывает ответ.
        Делает три попытки.
        :param query_dict: Входящие специфические для каждого запроса параметры
        :param not_debug: использовать/нет экономию запросов к hotels.com
        :return: None
        """
        data_par = {'headers': self.headers, self.query_name: query_dict, 'timeout': 6.1}
        for count_rec in range(3):
            try:
                response = requests.request(self.method, self.url, **data_par)
                response.raise_for_status()

                self.current_costs_response = response.headers.get('X-RateLimit-Requests-Remaining', None) # оставщиеся запросы
                self.limit_response = response.headers.get('X-RateLimit-Requests-Limit', None) # установленный лимит

                not_debug or print(f"Данные получены по запросу.\n{self.get_requests_limit_balance()}.")

                if response.status_code == requests.codes.ok:
                    self.status = True
                    self.json_encoders = response.json()
                    break
                else:
                    self.status = False
                    self.json_encoders = None
            except requests.exceptions.Timeout as err:
                pass
            except requests.exceptions.RequestException as err:
                self.status = False
                self.json_encoders = None
                break
            time.sleep(random.randint(1, 3))

    def read_json_file(self, file_name: str = "") -> bool:
        """
        Читает данные из указанного файла в атрибут json_encoders
        :param file_name:
        :return: True если файл прочитан
        """
        if file_name:
            file_name = file_name.strip().lower()
            try:
                with open(file_name, 'r', encoding='utf-8') as file_in:
                    self.json_encoders = json.loads(file_in.read())
                    self.status = True if self.json_encoders else False
                    return self.status
            except OSError as err:
                print(f">read_json_fil: файл {file_name} не найден.\n{err}")
        return False

    def write_json_file(self, file_name: str = "") -> bool:
        """
            Записывает данные в указанный файл из атрибута json_encoders
            :param file_name:
            :return: True если файл записан
        """
        if file_name:
            try:
                with open(file_name, "w", encoding='utf-8') as file_out:
                    if self.json_encoders:
                        json.dump(self.json_encoders, file_out, ensure_ascii=False)
                        self.status = True if self.json_encoders else False
                        return self.status
            except OSError as err:
                print(f">>write_json_file: файл {file_name} записать не удалось.\n{err}")
        return False

    def get_smart_data(self, query_dict: dict = None, data_file: str = "", not_debug: bool = True) -> None:
        """
        Для уменьшения количества обращений к серверу, данные берутся из файла, который создается при каждом запросе.
        Если файл с данными существует, то данные читаются из него, если файла еще нет,
        то отправляется запрос к серверу и полученные данные записываются в файл для дальнейшего использования.

        :param query_dict:
        :param data_file:
        :param not_debug:
        :return:
        """
        if data_file and os.path.exists(data_file):
            self.read_json_file(data_file)
            not_debug or print(f"Данные прочитаны их файла.")
        else:
            if query_dict:
                self.get_data(query_dict)
                not_debug or print(f"Данные получены по запросу.\n{self.get_requests_limit_balance()}.")
                if self.status and data_file:
                    self.write_json_file(data_file)


if __name__ == '__main__':
    # устанавливаем название региона
    target_place = "manchester"

    # записываем в настройки запроса регион который будем искать,
    # заполняем атрибуты класса 'tail_url', 'method', 'query_name' из экземпляра класса настроек
    # делаем запрос к hotels.com и записываем ответ в атрибут 'json_encoders', устанавливаем флаг 'status'
    # успешности получения данных
    # для уменьшения обращений к hotels.com записываем полученные данные в файл для уменьшения повторных вызовов
    site.set_target_place(target_place)
    place = SiteApi(**site.place.url)
    place.get_data(site.place.query, not_debug=False)
    # place.write_json_file(target_place + ".json")
    print(place.json_encoders.keys())

    # устанавливаем id региона
    target_offer = "2205"
    # записываем в настройки запроса id региона в котором будем искать отели,
    # заполняем даты и количества человек, устанавливаем количество ответов(отелей в предложении)
    # заполняем атрибуты класса 'tail_url', 'method', 'query_name' из экземпляра класса настроек
    # делаем запрос к hotels.com и записываем ответ в атрибут 'json_encoders', устанавливаем флаг 'status'
    # успешности получения данных
    site.set_target_destination(target_region_id=target_offer)
    site.set_dates(checkin_date="15/02/2023", checkout_date="22/02/2023")
    site.set_guests_numbers(adults=2, children=[2, 7])
    site.set_results_size(size=5)
    offer = SiteApi(**site.offer.url)
    offer.get_data(site.offer.query, not_debug=False)
    print(offer.json_encoders.keys())

    # устанавливаем id отеля 1223177  - Ramada by Wyndham Chorley South
    target_summary = "1223177"
    # записываем в настройки запроса id отеля для которого будем получать подробную информацию
    # делаем запрос к hotels.com и записываем ответ в атрибут 'json_encoders', устанавливаем флаг 'status
    site.set_property_id(property_id="1223177")
    summary = SiteApi(**site.summary.url)
    summary.get_data(site.summary.query, not_debug=False)
    print(summary.json_encoders.keys())

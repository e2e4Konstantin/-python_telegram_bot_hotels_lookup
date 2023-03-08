import sqlite3
from typing import Union, List
import json


class dbControl:
    """ Для управления ресурсами БД. """

    def __init__(self, db_file_name: str = None):
        self.db_file_name = db_file_name
        self.connect = None
        self.cursor = None

    def __enter__(self):
        """ Вызывается при старте контекстного менеджера.
        Возвращаемое значение, присваивается переменной x в конце выражения with as x.
        """
        self.connect_db()
        return self.cursor

    def __exit__(self, exception_type, exception_value, traceback):
        """ Будет вызван в завершении конструкции with, или в случае возникновения ошибки после нее. """
        self.close_db()

    def __str__(self):
        """ Строковое представление класса """
        return f"db name: {self.db_file_name}, connect: {self.connect}, cursor: {self.cursor}"

    def connect_db(self):
        """
        Соединяется с БД и инициирует курсор
        """
        try:
            self.connect = sqlite3.connect(self.db_file_name, check_same_thread=False)
            self.cursor = self.connect.cursor()
        except sqlite3.Error as err:
            if self.connect:
                self.connect.rollback()
            print(f"ошибка открытия БД Sqlite3: {err}")

    def close_db(self):
        """
            Записывает изменения в БД, закрывает соединение и курсор
        """
        if self.connect:
            self.connect.commit()
            self.cursor.close()
            self.connect.close()


class UsersActions:
    """ Класс для создания и для действий с указанной db_name БД."""
    db_name = 'history_bot.db'
    queries = {
        "CREATE_USERS_HISTORY_DB": """ /* Запрос для создания таблицы истории запросов в БД */ 
                CREATE TABLE IF NOT EXISTS history_users 
                ( 
                    story_id INTEGER PRIMARY KEY,                   
                    user_id INTEGER NOT NULL, 
                    date_time REAL NOT NULL,
                    user_name TEXT, 
                    chat_id INTEGER,
                    user_data TEXT                    -- json словарь с данными конвертированный в строку 
                );
                """,
        "INSERT_STORY_VAL": """
                    INSERT INTO history_users 
                        (user_id, date_time, user_name, chat_id, user_data) VALUES (?, ?, ?, ?, ?);
                    """,
        "INSERT_STORY_DICT": """
                    INSERT INTO history_users 
                        (user_id, date_time, user_name, chat_id, user_data) 
                        VALUES (:id, :dtime, :name, :chat, :data);
                    """,
        "GET_USER": """SELECT user_id AS [ID], user_name AS [Name], chat_id FROM history_users WHERE user_id = ?""",
        "SELECT_USER": """
                SELECT user_id, user_name, chat_id, date_time, user_data FROM history_users WHERE user_id =:id
                """,
        "SELECT_USER_SORT_LIMIT": """SELECT * FROM history_users WHERE user_id=? ORDER BY date_time DESC LIMIT ?""",
        "COUNT_ENTRIES": """SELECT COUNT(1) from history_users""",
        "SELECT_ALL": """SELECT * from history_users""",
        "DELETE_ALL": """DELETE FROM history_users""",
        "CREATE_CONSTANT_DB": """
                CREATE TABLE IF NOT EXISTS constants         -- создание таблицы для хранения констант пользователей 
                (
                    user_id INTEGER PRIMARY KEY, 
                    image_size INTEGER NOT NULL DEFAULT 10,  -- количество изображений отеля в выдаче
                    result_size INTEGER NOT NULL DEFAULT 9,  -- количество отелей в выдаче   
                    story_size INTEGER NOT NULL DEFAULT 6    -- количество результатов в выдаче истории запросов
                );
        """,
        "SELECT_CONSTANTS": """SELECT image_size, result_size, story_size FROM constants WHERE user_id = ?;""",
        "INSERT_CONSTANTS": """INSERT INTO constants (user_id, image_size, result_size, story_size) VALUES (?, ?, ?, ?);""",
        "UPDATE_CONSTANTS": """UPDATE constants SET image_size = ?, result_size=?, story_size=? WHERE user_id = ?;""",

    }

    def __init__(self, name_file_db: str = ""):
        """
        В указанном файле БД создаются две таблицы, для хранения истории запросов пользователей и для
        хранения кофигов пользователей

        """
        if name_file_db:
            self.db = dbControl(name_file_db)
        else:
            self.db = dbControl(self.db_name)
        try:
            with self.db as cur:
                cur.execute(self.queries.get('CREATE_USERS_HISTORY_DB', None))
                cur.execute(self.queries.get('CREATE_CONSTANT_DB', None))
        except sqlite3.Error as err:
            print(f"ошибка создания в БД Sqlite3: {err}")

    def inform_db(self, all_details: bool = False):
        """
        Выводи в консоль информацию о таблицах БД
        :param all_details: выводить все записи
        """
        with self.db as cur:
            cur.execute('SELECT SQLITE_VERSION()')
            print(f"SQLite version: {cur.fetchone()[0]}")
            print(f"connect.total_changes: {self.db.connect.total_changes}")

            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cur.fetchall()
            for index, table_i in enumerate(tables):
                table_name = table_i[0]
                count = cur.execute(f"SELECT COUNT(1) from {table_name}")
                print(f"\n{index + 1}. таблица: {table_name}, записей: {count.fetchone()[0]}")
                table_info = cur.execute(f"PRAGMA table_info({table_name})")
                data = table_info.fetchall()

                print(f"поля таблицы: ")
                [print(f"\t{d}") for d in data]
                if all_details:
                    print(f"данные таблицы:")
                    cur.execute(f"SELECT * from {table_name}")
                    [print(row_i) for row_i in cur]

    def delete_all_records(self) -> None:
        """ Удаляет все записи из таблицы history_users БД """
        with self.db as cursor:
            try:
                cursor.execute(self.queries.get("DELETE_ALL", None))
                print("Все записи в БД успешно удалены")
            except sqlite3.Error as err:
                print("Ошибка при удалении записей SQLite", err)

    def get_user_id(self, user_id: int) -> Union[List, None]:
        """ Возвращает все записи из таблицы history_users для user_id  """
        with self.db as cursor:
            cursor.execute(self.queries.get('SELECT_USER', None), {"id": user_id})
            data = cursor.fetchall()
        return data if data else None

    def get_user_sortingtime_limit(self, user_id: int, row_limit: int) -> Union[List, None]:
        """ Возвращает все записи из таблицы history_users для user_id отсортированные по времени """
        with self.db as cursor:
            cursor.execute(self.queries.get('SELECT_USER_SORT_LIMIT', None), (user_id, row_limit))
            data = cursor.fetchall()
        return data if data else None

    def add_user_data(self, user_id: int, date_time: float, user_name: str, chat_id: int, user_data: dict) -> bool:
        """ Записывает новую строку в таблицу history_users """
        if user_id and date_time and user_data:
            byte_data = json.dumps(user_data)
            with self.db as cursor:
                try:
                    cursor.execute(self.queries.get('INSERT_STORY_VAL', None),
                                   (user_id, date_time, user_name, chat_id, byte_data))
                    return True
                except sqlite3.Error as err:
                    if self.db.connect:
                        self.db.connect.rollback()
                    print(f"ошибка записи в БД Sqlite3: {err}")
                    return False

    def get_user_constant(self, user_id: int) -> Union[tuple, None]:
        """ Возвращает значения полей из таблицы constants user_id """
        with self.db as cursor:
            cursor.execute(self.queries.get('SELECT_CONSTANTS', None), (user_id,))
            data = cursor.fetchone()
        return data if data else None

    def init_user_constant(self, user_id: int, image_size: int, result_size: int, story_size: int) -> bool:
        """ Создает запись в таблице constants БД с указанными константами для user_id """
        with self.db as cursor:
            cursor.execute(self.queries.get('SELECT_CONSTANTS', None), (user_id,))
            data = cursor.fetchone()
            if data is None:
                cursor.execute(self.queries.get('INSERT_CONSTANTS', None),
                               (user_id, image_size, result_size, story_size))
                return True
        return False

    def set_user_constant(self, user_id: int, image_size: int, result_size: int, story_size: int) -> bool:
        """ Меняет значения полей в таблице constants для user_id """
        try:
            with self.db as cur:
                cur.execute(self.queries.get('UPDATE_CONSTANTS', None), (image_size, result_size, story_size, user_id))
                if cur.rowcount >= 1:
                    return True
                return False
        except sqlite3.Error as err:
            print(f"ошибка изменения таблицы constants БД Sqlite3: {err}")
        return False


if __name__ == '__main__':
    u = UsersActions("../history_bot.db")
    u.inform_db()
    # u.delete_all_records()
    row = u.get_user_sortingtime_limit(818709561, 5)
    if row:
        [print(x) for x in row]

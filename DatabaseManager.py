import sys
import datetime

import psycopg2
from psycopg2 import extras

DB_CONFIG = {
    'dbname': 'pm_05',
    'user': 'postgres',
    'password': '123456',
    'host': 'localhost',
    'port': '5432'
}
class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            print("Успешное подключение к базе данных")
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            sys.exit(1)

    # Проверяем, есть ли администратор по умолчанию
    def create_tables(self):
        try:
            cursor = self.conn.cursor()

            # Проверяем, есть ли администратор по умолчанию
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Администратор'")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO users (login, password, role) VALUES (%s, %s, %s)",
                    ('admin', 'admin', 'Администратор')
                )

            self.conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Ошибка создания таблиц: {e}")

    def authenticate_user(self, login, password):
        cursor = self.conn.cursor()

        # Проверка блокировки
        cursor.execute("SELECT is_blocked FROM users WHERE login = %s", (login,))
        result = cursor.fetchone()

        if result and result[0]:
            cursor.close()
            return None, "blocked"

        # Проверка учетных данных
        cursor.execute(
            "SELECT id, password, role, login_attempts, password_change_required FROM users WHERE login = %s",
            (login,)
        )
        user = cursor.fetchone()

        if user and password == user[1]:
            # Успешная авторизация
            user_id, _, role, _, password_change_required = user

            # Сбрасываем счетчик попыток и обновляем дату последнего входа
            cursor.execute(
                "UPDATE users SET login_attempts = 0, last_login = %s WHERE id = %s",
                (datetime.datetime.now(), user_id)
            )
            self.conn.commit()
            cursor.close()

            return {
                'id': user_id,
                'login': login,
                'role': role,
                'password_change_required': password_change_required
            }, "success"
        else:
            # Неудачная попытка входа
            if user:
                user_id = user[0]
                attempts = user[3] + 1

                if attempts >= 3:
                    # Блокируем пользователя
                    cursor.execute(
                        "UPDATE users SET login_attempts = %s, is_blocked = TRUE WHERE id = %s",
                        (attempts, user_id)
                    )
                else:
                    # Увеличиваем счетчик попыток
                    cursor.execute(
                        "UPDATE users SET login_attempts = %s WHERE id = %s",
                        (attempts, user_id)
                    )

                self.conn.commit()

            cursor.close()
            return None, "invalid"

    def change_password(self, user_id, current_password, new_password):
        cursor = self.conn.cursor()

        # Проверяем текущий пароль
        cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        stored_password = cursor.fetchone()[0]

        if current_password != stored_password:
            cursor.close()
            return False, "Текущий пароль введен неверно"

        # Обновляем пароль
        cursor.execute(
            "UPDATE users SET password = %s, password_change_required = FALSE WHERE id = %s",
            (new_password, user_id)
        )

        self.conn.commit()
        cursor.close()
        return True, "Пароль успешно изменен"

    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, login, role, is_blocked FROM users")
        users = cursor.fetchall()
        cursor.close()
        return users

    def add_user(self, login, password, role):
        cursor = self.conn.cursor()

        # Проверяем, существует ли пользователь
        cursor.execute("SELECT COUNT(*) FROM users WHERE login = %s", (login,))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            return False, "Пользователь с таким логином уже существует"

        # Добавляем пользователя
        cursor.execute(
            "INSERT INTO users (login, password, role, password_change_required) VALUES (%s, %s, %s, TRUE)",
            (login, password, role)
        )

        self.conn.commit()
        cursor.close()
        return True, "Пользователь успешно добавлен"


    def update_user(self, user_id, role, is_blocked):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET role = %s, is_blocked = %s WHERE id = %s",
            (role, is_blocked, user_id)
        )

        self.conn.commit()
        cursor.close()
        return True, "Данные пользователя успешно обновлены"

    def check_inactive_users(self):
        cursor = self.conn.cursor()

        # Блокируем пользователей, которые не входили более 1 месяца
        month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        cursor.execute(
            "UPDATE users SET is_blocked = TRUE WHERE last_login < %s OR last_login IS NULL",
            (month_ago,)
        )

        count = cursor.rowcount
        self.conn.commit()
        cursor.close()
        return count

    def execute_query(self, query, params=None, fetch=False):
        """
        Выполняет SQL-запрос к базе данных.

        Args:
            query (str): SQL-запрос для выполнения
            params (tuple, optional): Параметры для запроса
            fetch (bool, optional): Если True, возвращает результат запроса

        Returns:
            list/None: Результат запроса, если fetch=True, иначе None
        """
        cursor = None
        try:
            # Создание курсора
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # Выполнение запроса
            cursor.execute(query, params or ())

            # Получение результата, если требуется
            result = None
            if fetch:
                result = cursor.fetchall()

            # Фиксация изменений
            self.conn.commit()

            return result

        except psycopg2.Error as e:
            # Откат изменений в случае ошибки
            self.conn.rollback()

            # Логирование ошибки
            print(f"Ошибка выполнения запроса: {e}")

            # Пробрасывание ошибки выше для обработки в вызывающем коде
            raise e

        finally:
            # Закрытие курсора
            if cursor:
                cursor.close()

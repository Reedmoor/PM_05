import sys
import datetime

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QHBoxLayout, QMessageBox, QGridLayout,
                             QTableWidget, QTableWidgetItem, QComboBox, QMainWindow, QSizePolicy, QTabWidget,
                             QFormLayout, QDateTimeEdit, QDialog, QSplitter, QGroupBox, QDoubleSpinBox,
                             QDialogButtonBox, QHeaderView, QDateEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime, QDate
import psycopg2
from psycopg2 import extras

# Конфигурация подключения к базе данных
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

class LoginWindow(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Авторизация')
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()

        # Поля для ввода логина и пароля
        form_layout = QGridLayout()

        login_label = QLabel('Логин:')
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText('Введите логин')
        form_layout.addWidget(login_label, 0, 0)
        form_layout.addWidget(self.login_input, 0, 1)

        password_label = QLabel('Пароль:')
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Введите пароль')
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)

        layout.addLayout(form_layout)

        # Кнопка входа
        self.login_button = QPushButton('Войти')
        self.login_button.clicked.connect(self.authenticate)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def authenticate(self):
        login = self.login_input.text()
        password = self.password_input.text()

        # Проверка заполнения полей
        if not login or not password:
            QMessageBox.warning(self, 'Ошибка', 'Необходимо заполнить все поля')
            return

        # Аутентификация
        user, status = self.db_manager.authenticate_user(login, password)

        if status == "blocked":
            QMessageBox.critical(self, 'Ошибка', 'Вы заблокированы. Обратитесь к администратору')
        elif status == "invalid":
            QMessageBox.warning(self, 'Ошибка',
                                'Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные')
        elif status == "success":
            QMessageBox.information(self, 'Успех', 'Вы успешно авторизовались')

            # Проверка необходимости смены пароля
            if user['password_change_required']:
                self.password_change_window = PasswordChangeWindow(self.db_manager, user['id'])
                self.password_change_window.show()
                self.password_change_window.password_changed.connect(self.on_password_changed)
                self.hide()
            else:
                self.open_main_window(user)

    def on_password_changed(self, success):
        if success:
            # Получаем обновленные данные пользователя
            cursor = self.db_manager.conn.cursor()
            cursor.execute("SELECT id, login, role FROM users WHERE id = %s",
                           (self.password_change_window.user_id,))
            user_data = cursor.fetchone()
            cursor.close()

            user = {
                'id': user_data[0],
                'login': user_data[1],
                'role': user_data[2],
                'password_change_required': False
            }

            self.open_main_window(user)

    def open_main_window(self, user):
        print(f"Opening window for user: {user}")
        print(f"User role: {user.get('role')}")
        print(f"DB Manager: {self.db_manager}")

        try:
            if user['role'] == 'Администратор':
                self.main_window = AdminMainWindow(self.db_manager, user)
            else:
                self.main_window = UserMainWindow(self.db_manager, user)

            self.main_window.show()
            self.close()
        except Exception as e:
            print(f"Detailed error opening main window: {e}")
            import traceback
            traceback.print_exc()

class PasswordChangeWindow(QWidget):
    password_changed = pyqtSignal(bool)

    def __init__(self, db_manager, user_id):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Смена пароля')
        self.setFixedSize(400, 250)

        layout = QVBoxLayout()

        message = QLabel('При первом входе необходимо сменить пароль')
        message.setAlignment(Qt.AlignCenter)
        layout.addWidget(message)

        form_layout = QGridLayout()

        current_label = QLabel('Текущий пароль:')
        self.current_input = QLineEdit()
        self.current_input.setPlaceholderText('Введите текущий пароль')
        self.current_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(current_label, 0, 0)
        form_layout.addWidget(self.current_input, 0, 1)

        new_label = QLabel('Новый пароль:')
        self.new_input = QLineEdit()
        self.new_input.setPlaceholderText('Введите новый пароль')
        self.new_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(new_label, 1, 0)
        form_layout.addWidget(self.new_input, 1, 1)

        confirm_label = QLabel('Подтверждение:')
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText('Подтвердите новый пароль')
        self.confirm_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(confirm_label, 2, 0)
        form_layout.addWidget(self.confirm_input, 2, 1)

        layout.addLayout(form_layout)

        self.change_button = QPushButton('Изменить пароль')
        self.change_button.clicked.connect(self.change_password)
        layout.addWidget(self.change_button)

        self.setLayout(layout)

    def change_password(self):
        current = self.current_input.text()
        new_password = self.new_input.text()
        confirm = self.confirm_input.text()

        # Проверка заполнения полей
        if not current or not new_password or not confirm:
            QMessageBox.warning(self, 'Ошибка', 'Необходимо заполнить все поля')
            return

        # Проверка совпадения паролей
        if new_password != confirm:
            QMessageBox.warning(self, 'Ошибка', 'Новый пароль и подтверждение не совпадают')
            return

        # Смена пароля
        success, message = self.db_manager.change_password(self.user_id, current, new_password)

        if success:
            QMessageBox.information(self, 'Успех', message)
            self.password_changed.emit(True)
            self.close()
        else:
            QMessageBox.warning(self, 'Ошибка', message)

class AdminMainWindow(QMainWindow):
    def __init__(self, db_manager, user):
        super().__init__()
        self.db_manager = db_manager
        self.user = user
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Панель администратора')
        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        welcome_label = QLabel(f'Добро пожаловать, {self.user["login"]} (Администратор)')
        welcome_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(welcome_label)

        buttons_layout = QHBoxLayout()

        self.add_user_button = QPushButton('Добавить пользователя')
        self.add_user_button.clicked.connect(self.show_add_user_dialog)
        buttons_layout.addWidget(self.add_user_button)

        self.refresh_button = QPushButton('Обновить список')
        self.refresh_button.clicked.connect(self.load_users)
        buttons_layout.addWidget(self.refresh_button)

        main_layout.addLayout(buttons_layout)

        # Таблица пользователей
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(['ID', 'Логин', 'Роль', 'Статус', 'Действия'])
        self.users_table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.users_table)

        self.setCentralWidget(central_widget)

        # Загрузка пользователей
        self.load_users()

    def load_users(self):
        users = self.db_manager.get_all_users()

        self.users_table.setRowCount(len(users))

        for row, user in enumerate(users):
            user_id, login, role, is_blocked = user

            # ID
            id_item = QTableWidgetItem(str(user_id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.users_table.setItem(row, 0, id_item)

            # Логин
            login_item = QTableWidgetItem(login)
            login_item.setFlags(login_item.flags() & ~Qt.ItemIsEditable)
            self.users_table.setItem(row, 1, login_item)

            # Роль (выпадающий список)
            role_combo = QComboBox()
            role_combo.addItems(['Администратор', 'Пользователь'])
            role_combo.setCurrentText(role)
            self.users_table.setCellWidget(row, 2, role_combo)

            # Статус (выпадающий список)
            status_combo = QComboBox()
            status_combo.addItems(['Активен', 'Заблокирован'])
            status_combo.setCurrentIndex(1 if is_blocked else 0)
            self.users_table.setCellWidget(row, 3, status_combo)

            # Кнопка сохранения
            save_button = QPushButton('Сохранить')
            save_button.clicked.connect(lambda checked, r=row: self.save_user_changes(r))
            self.users_table.setCellWidget(row, 4, save_button)

    def save_user_changes(self, row):
        user_id = int(self.users_table.item(row, 0).text())
        role_combo = self.users_table.cellWidget(row, 2)
        status_combo = self.users_table.cellWidget(row, 3)

        role = role_combo.currentText()
        is_blocked = status_combo.currentIndex() == 1

        success, message = self.db_manager.update_user(user_id, role, is_blocked)

        if success:
            QMessageBox.information(self, 'Успех', message)
        else:
            QMessageBox.warning(self, 'Ошибка', message)

    def show_add_user_dialog(self):
        self.add_user_dialog = AddUserDialog(self.db_manager)
        self.add_user_dialog.user_added.connect(self.load_users)
        self.add_user_dialog.show()


class AddUserDialog(QWidget):
    user_added = pyqtSignal()

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Добавление пользователя')
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()

        form_layout = QGridLayout()

        login_label = QLabel('Логин:')
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText('Введите логин')
        form_layout.addWidget(login_label, 0, 0)
        form_layout.addWidget(self.login_input, 0, 1)

        password_label = QLabel('Пароль:')
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Введите пароль')
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)

        role_label = QLabel('Роль:')
        self.role_combo = QComboBox()
        self.role_combo.addItems(['Администратор', 'Пользователь'])
        form_layout.addWidget(role_label, 2, 0)
        form_layout.addWidget(self.role_combo, 2, 1)

        layout.addLayout(form_layout)

        self.add_button = QPushButton('Добавить')
        self.add_button.clicked.connect(self.add_user)
        layout.addWidget(self.add_button)

        self.setLayout(layout)

    def add_user(self):
        login = self.login_input.text()
        password = self.password_input.text()
        role = self.role_combo.currentText()

        if not login or not password:
            QMessageBox.warning(self, 'Ошибка', 'Необходимо заполнить все поля')
            return

        success, message = self.db_manager.add_user(login, password, role)

        if success:
            QMessageBox.information(self, 'Успех', message)
            self.user_added.emit()
            self.close()
        else:
            QMessageBox.warning(self, 'Ошибка', message)


class UserMainWindow(QMainWindow):
    def __init__(self, db_manager, user):
        super().__init__()
        self.db_manager = db_manager
        self.user = user
        self.init_ui()


    def init_ui(self):
        self.setWindowTitle('Личный кабинет')
        self.setMinimumSize(800, 600)

        # Центральный виджет
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Приветствие
        welcome_label = QLabel(f'Добро пожаловать, {self.user["login"]}')
        welcome_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(welcome_label)

        # Информация о пользователе
        info_layout = QGridLayout()

        login_label = QLabel('Логин:')
        login_value = QLabel(self.user["login"])
        info_layout.addWidget(login_label, 0, 0)
        info_layout.addWidget(login_value, 0, 1)

        role_label = QLabel('Роль:')
        role_value = QLabel(self.user["role"])
        info_layout.addWidget(role_label, 1, 0)
        info_layout.addWidget(role_value, 1, 1)

        main_layout.addLayout(info_layout)

        # Кнопка смены пароля
        self.change_password_button = QPushButton('Сменить пароль')
        self.change_password_button.clicked.connect(self.show_change_password_dialog)
        main_layout.addWidget(self.change_password_button)

        # Вкладки
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        """БРОНИРОВАНИЕ"""

        # Вкладка для добавления постояльца
        guest_tab = QWidget()
        guest_layout = QVBoxLayout(guest_tab)
        tabs.addTab(guest_tab, "Добавление постояльца")

        # Форма добавления постояльца
        guest_form_layout = QFormLayout()

        self.name_input = QLineEdit()
        guest_form_layout.addRow("Имя:", self.name_input)

        self.surname_input = QLineEdit()
        guest_form_layout.addRow("Фамилия:", self.surname_input)

        self.patronymic_input = QLineEdit()
        self.patronymic_input.setPlaceholderText("Необязательно")
        guest_form_layout.addRow("Отчество", self.patronymic_input)

        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("Необязательно")
        guest_form_layout.addRow("Мобильный телефон:", self.mobile_input)

        self.passport_input = QLineEdit()
        guest_form_layout.addRow("Паспорт:", self.passport_input)

        guest_layout.addLayout(guest_form_layout)

        self.add_guest_button = QPushButton("Добавить постояльца")
        self.add_guest_button.clicked.connect(self.add_guest)
        guest_layout.addWidget(self.add_guest_button)

        # Вкладка для бронирования и комнат
        booking_tab = QWidget()
        booking_layout = QVBoxLayout(booking_tab)
        tabs.addTab(booking_tab, "Бронирование комнат")

        # Сплиттер для разделения формы бронирования и таблицы комнат
        splitter = QSplitter(Qt.Vertical)
        booking_layout.addWidget(splitter)

        # Верхняя часть - форма бронирования
        booking_form_widget = QWidget()
        booking_form_layout = QFormLayout(booking_form_widget)

        self.guest_combobox = QComboBox()
        self.update_guest_combobox()
        booking_form_layout.addRow("Постоялец:", self.guest_combobox)

        self.check_in_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.check_in_date.setCalendarPopup(True)
        booking_form_layout.addRow("Дата и время заселения:", self.check_in_date)

        self.check_out_date = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.check_out_date.setCalendarPopup(True)
        booking_form_layout.addRow("Дата и время выселения:", self.check_out_date)

        # Кнопка для поиска доступных комнат
        self.find_rooms_button = QPushButton("Найти доступные комнаты")
        self.find_rooms_button.clicked.connect(self.find_available_rooms)
        booking_form_layout.addRow("", self.find_rooms_button)

        splitter.addWidget(booking_form_widget)

        # Нижняя часть - таблица комнат
        rooms_widget = QWidget()
        rooms_layout = QVBoxLayout(rooms_widget)

        # Таблица комнат
        self.rooms_table = QTableWidget()
        self.rooms_table.setColumnCount(5)
        self.rooms_table.setHorizontalHeaderLabels(["Этаж", "Номер", "Категория","Стоимость", "ID",])
        self.rooms_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rooms_table.setSelectionMode(QTableWidget.SingleSelection)
        self.rooms_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rooms_table.setColumnHidden(4, True)  # Скрываем колонку с ID

        rooms_layout.addWidget(self.rooms_table)

        # Кнопка для бронирования выбранной комнаты
        self.book_room_button = QPushButton("Забронировать выбранную комнату")
        self.book_room_button.clicked.connect(self.book_room)
        rooms_layout.addWidget(self.book_room_button)

        splitter.addWidget(rooms_widget)

        # Устанавливаем начальные размеры сплиттера
        splitter.setSizes([200, 400])

        # Обновить список комнат
        self.update_rooms_table()

        self.setCentralWidget(central_widget)

        """УСЛУГИ"""

        # Вкладка для услуг
        services_tab = QWidget()
        services_layout = QVBoxLayout(services_tab)
        tabs.addTab(services_tab, "Услуги")

        # Сплиттер для разделения формы добавления услуги и таблицы услуг
        services_splitter = QSplitter(Qt.Vertical)
        services_layout.addWidget(services_splitter)

        # Верхняя часть - форма добавления услуги гостю
        service_form_widget = QWidget()
        service_form_layout = QFormLayout(service_form_widget)

        self.service_guest_combobox = QComboBox()
        self.update_guest_combobox(self.service_guest_combobox)  # Переиспользуем метод обновления списка гостей
        service_form_layout.addRow("Постоялец:", self.service_guest_combobox)

        self.service_combobox = QComboBox()
        self.update_services_combobox()  # Нужно будет создать этот метод
        service_form_layout.addRow("Услуга:", self.service_combobox)

        self.service_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.service_date.setCalendarPopup(True)
        service_form_layout.addRow("Дата и время:", self.service_date)

        # Кнопка для добавления услуги гостю
        self.add_service_button = QPushButton("Добавить услугу")
        self.add_service_button.clicked.connect(self.add_service_for_guest)
        service_form_layout.addRow("", self.add_service_button)

        services_splitter.addWidget(service_form_widget)

        # Нижняя часть - таблица услуг гостя
        guest_services_widget = QWidget()
        guest_services_layout = QVBoxLayout(guest_services_widget)

        # Заголовок таблицы
        self.guest_services_label = QLabel("Услуги постояльца")
        self.guest_services_label.setAlignment(Qt.AlignCenter)
        guest_services_layout.addWidget(self.guest_services_label)

        # Таблица услуг гостя
        self.guest_services_table = QTableWidget()
        self.guest_services_table.setColumnCount(4)
        self.guest_services_table.setHorizontalHeaderLabels(["Услуга", "Цена", "Дата", "ID"])
        self.guest_services_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.guest_services_table.setSelectionMode(QTableWidget.SingleSelection)
        self.guest_services_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.guest_services_table.setColumnHidden(3, True)  # Скрываем колонку с ID

        guest_services_layout.addWidget(self.guest_services_table)

        # Кнопка для удаления выбранной услуги
        self.delete_service_button = QPushButton("Удалить выбранную услугу")
        self.delete_service_button.clicked.connect(self.delete_service_for_guest)
        guest_services_layout.addWidget(self.delete_service_button)

        services_splitter.addWidget(guest_services_widget)

        # Устанавливаем начальные размеры сплиттера
        services_splitter.setSizes([200, 400])

        # Обработчик изменения выбранного гостя
        self.service_guest_combobox.currentIndexChanged.connect(self.update_guest_services_table)

    # Дополняем вкладку услуг в методе init_ui
        # Добавляем вкладки внутри вкладки услуг
        services_tabs = QTabWidget()
        services_layout.addWidget(services_tabs)

        # Перемещаем существующие виджеты для услуг постояльцев на первую вкладку
        guest_services_container = QWidget()
        guest_services_container_layout = QVBoxLayout(guest_services_container)
        guest_services_container_layout.addWidget(services_splitter)
        services_tabs.addTab(guest_services_container, "Услуги постояльцев")

        # Создаем вкладку для управления списком услуг
        manage_services_tab = QWidget()
        manage_services_layout = QVBoxLayout(manage_services_tab)
        services_tabs.addTab(manage_services_tab, "Управление услугами")

        # Таблица доступных услуг
        self.services_table = QTableWidget()
        self.services_table.setColumnCount(3)
        self.services_table.setHorizontalHeaderLabels(["Название", "Цена (руб.)", "ID"])
        self.services_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.services_table.setSelectionMode(QTableWidget.SingleSelection)
        self.services_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.services_table.setColumnHidden(2, True)  # Скрываем колонку с ID
        manage_services_layout.addWidget(self.services_table)

        # Форма для добавления/редактирования услуги
        service_edit_group = QGroupBox("Добавление/редактирование услуги")
        service_edit_layout = QFormLayout(service_edit_group)

        self.service_title_input = QLineEdit()
        service_edit_layout.addRow("Название:", self.service_title_input)

        self.service_price_input = QDoubleSpinBox()
        self.service_price_input.setRange(0.0, 1000000.0)
        self.service_price_input.setDecimals(2)
        self.service_price_input.setSuffix(" руб.")
        service_edit_layout.addRow("Цена:", self.service_price_input)

        # Скрытое поле для ID редактируемой услуги
        self.service_edit_id = None

        # Кнопки действий
        service_buttons_layout = QHBoxLayout()
        self.add_service_to_list_button = QPushButton("Добавить")
        self.add_service_to_list_button.clicked.connect(self.add_service_to_list)
        service_buttons_layout.addWidget(self.add_service_to_list_button)

        self.edit_service_button = QPushButton("Редактировать выбранную")
        self.edit_service_button.clicked.connect(self.edit_service)
        service_buttons_layout.addWidget(self.edit_service_button)

        self.delete_service_from_list_button = QPushButton("Удалить выбранную")
        self.delete_service_from_list_button.clicked.connect(self.delete_service_from_list)
        service_buttons_layout.addWidget(self.delete_service_from_list_button)

        service_edit_layout.addRow("", service_buttons_layout)
        manage_services_layout.addWidget(service_edit_group)

        # Обновляем таблицу услуг
        self.update_services_table()
        self.update_services_combobox()
        self.update_guest_services_table()

        """ОТЧЕТЫ"""

        # Вкладка "Отчеты"
        reports_tab = QWidget()
        reports_layout = QVBoxLayout(reports_tab)
        tabs.addTab(reports_tab, "Отчеты")

        # Создаем виджет для подвкладок
        reports_subtabs = QTabWidget()
        reports_layout.addWidget(reports_subtabs)

        # Вкладка "Отчеты по номерам"
        room_reports_tab = QWidget()
        room_reports_layout = QVBoxLayout(room_reports_tab)
        reports_subtabs.addTab(room_reports_tab, "Отчеты по номерам")

        # Верхняя панель с фильтрами
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Номер:"))
        self.room_selector = QComboBox()
        filter_layout.addWidget(self.room_selector)

        filter_layout.addWidget(QLabel("С:"))
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("По:"))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filter_layout.addWidget(self.date_to)

        refresh_button = QPushButton("Сформировать")
        refresh_button.clicked.connect(self.generate_room_report)
        filter_layout.addWidget(refresh_button)
        room_reports_layout.addLayout(filter_layout)

        # Панель с показателями
        metrics_layout = QGridLayout()
        metrics_layout.addWidget(QLabel("<b>Показатель</b>"), 0, 0)
        metrics_layout.addWidget(QLabel("<b>Значение</b>"), 0, 1)

        metrics_layout.addWidget(QLabel("Выручка:"), 1, 0)
        self.revenue_label = QLabel("0 руб.")
        metrics_layout.addWidget(self.revenue_label, 1, 1)

        metrics_layout.addWidget(QLabel("Бронирований:"), 2, 0)
        self.bookings_label = QLabel("0")
        metrics_layout.addWidget(self.bookings_label, 2, 1)

        metrics_layout.addWidget(QLabel("Загрузка:"), 3, 0)
        self.occupancy_label = QLabel("0%")
        metrics_layout.addWidget(self.occupancy_label, 3, 1)

        metrics_layout.addWidget(QLabel("ADR:"), 4, 0)
        self.adr_label = QLabel("0 руб.")
        metrics_layout.addWidget(self.adr_label, 4, 1)

        metrics_layout.addWidget(QLabel("RevPAR:"), 5, 0)
        self.revpar_label = QLabel("0 руб.")
        metrics_layout.addWidget(self.revpar_label, 5, 1)

        room_reports_layout.addLayout(metrics_layout)

        # Таблица бронирований
        self.bookings_table = QTableWidget()
        self.bookings_table.setColumnCount(6)
        self.bookings_table.setHorizontalHeaderLabels(["Гость", "Заезд", "Выезд", "Ночей", "Стоимость", "Доп. услуги"])
        self.bookings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        room_reports_layout.addWidget(self.bookings_table)

        # Загружаем список номеров
        self.load_rooms()

        """УБОРКА"""

        cleaning_tab = QWidget()
        cleaning_layout = QVBoxLayout(cleaning_tab)
        tabs.addTab(cleaning_tab, "Уборка номеров")

        # Заголовок
        cleaning_title = QLabel("Номера, требующие уборки")
        cleaning_title.setAlignment(Qt.AlignCenter)
        cleaning_layout.addWidget(cleaning_title)

        # Таблица с грязными номерами
        self.dirty_rooms_table = QTableWidget()
        self.dirty_rooms_table.setColumnCount(5)
        self.dirty_rooms_table.setHorizontalHeaderLabels(["ID", "Номер", "Этаж", "Категория", "Действие"])
        self.dirty_rooms_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dirty_rooms_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dirty_rooms_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cleaning_layout.addWidget(self.dirty_rooms_table)

        # Кнопка для обновления списка
        refresh_button = QPushButton("Обновить список")
        refresh_button.clicked.connect(self.load_dirty_rooms)
        cleaning_layout.addWidget(refresh_button)
        # Загружаем данные при инициализации
        self.load_dirty_rooms()

        self.setCentralWidget(central_widget)

    def load_dirty_rooms(self):
        # Очищаем таблицу
        self.dirty_rooms_table.setRowCount(0)

        try:
            # Сначала обновляем статусы номеров на основе дат выселения
            update_status_query = """
                UPDATE room r
                SET status = 'грязный'
                FROM reservation b
                WHERE r.id = b.id_room
                AND b.check_out_time IS NOT NULL
                AND b.check_out_time <= CURRENT_TIMESTAMP
                AND r.status = 'Занят'
            """
            self.db_manager.execute_query(update_status_query)

            # Получаем список грязных номеров из БД
            query = """
                SELECT id, number, floor, category
                FROM room
                WHERE status = 'грязный'
                ORDER BY floor, number
            """
            dirty_rooms = self.db_manager.execute_query(query, fetch=True)

            # Настраиваем таблицу
            self.dirty_rooms_table.setColumnCount(5)
            self.dirty_rooms_table.setHorizontalHeaderLabels(["ID", "Номер", "Этаж", "Категория", "Действие"])
            self.dirty_rooms_table.setColumnHidden(0, True)  # Скрываем колонку с ID

            # Заполняем таблицу
            for i, room in enumerate(dirty_rooms):
                self.dirty_rooms_table.insertRow(i)
                self.dirty_rooms_table.setItem(i, 0, QTableWidgetItem(str(room['id'])))
                self.dirty_rooms_table.setItem(i, 1, QTableWidgetItem(str(room['number'])))
                self.dirty_rooms_table.setItem(i, 2, QTableWidgetItem(str(room['floor'])))
                self.dirty_rooms_table.setItem(i, 3, QTableWidgetItem(str(room['category'])))

                # Добавляем кнопку уборки
                clean_button = QPushButton("Отметить как убранный")
                clean_button.clicked.connect(lambda checked, room_id=room['id']: self.mark_room_as_cleaned(room_id))
                self.dirty_rooms_table.setCellWidget(i, 4, clean_button)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список грязных номеров: {str(e)}")

    def mark_room_as_cleaned(self, room_id):
        try:
            # Простой запрос на обновление статуса номера с "грязный" на "свободный"
            update_query = "UPDATE room SET status = 'свободный' WHERE id = %s"
            self.db_manager.execute_query(update_query, (room_id,))

            # Обновляем список
            self.load_dirty_rooms()
            QMessageBox.information(self, "Успех", "Номер отмечен как убранный")

        except Exception as e:
            # Выводим подробную информацию об ошибке
            import traceback
            error_details = traceback.format_exc()
            print(error_details)
            QMessageBox.critical(self, "Ошибка", f"Не удалось отметить номер как убранный: {str(e)}")
    def setup_room_status_trigger(self):
        """
        Создает триггер в базе данных для автоматического изменения статуса номера
        на "грязный" после выселения гостя
        """
        try:
            # Создаем функцию для триггера
            trigger_function_query = """
                CREATE OR REPLACE FUNCTION update_room_status_after_checkout()
                RETURNS TRIGGER AS $$
                BEGIN
                    UPDATE room SET status = 'грязный' 
                    WHERE id = (SELECT id_room FROM booking WHERE id = NEW.id);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            self.db_manager.execute_query(trigger_function_query)

            # Создаем сам триггер
            trigger_query = """
                DROP TRIGGER IF EXISTS after_checkout_trigger ON booking;
                CREATE TRIGGER after_checkout_trigger
                AFTER UPDATE OF checkout_date ON booking
                FOR EACH ROW
                WHEN (NEW.checkout_date IS NOT NULL AND OLD.checkout_date IS NULL)
                EXECUTE FUNCTION update_room_status_after_checkout();
                """
            self.db_manager.execute_query(trigger_query)

        except Exception as e:
            print(f"Ошибка при создании триггера: {str(e)}")

    def load_rooms(self):
        try:
            rooms = self.db_manager.execute_query(
                "SELECT id, floor, number, category FROM room ORDER BY floor, number",
                fetch=True
            )

            self.room_selector.clear()
            self.room_selector.addItem("Все номера", None)

            for room in rooms:
                self.room_selector.addItem(f"Этаж {room['floor']}, №{room['number']} ({room['category']})", room['id'])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить номера: {str(e)}")

    # Генерация отчета по номеру
    def generate_room_report(self):
        try:
            start_date = self.date_from.date().toString("yyyy-MM-dd")
            end_date = self.date_to.date().toString("yyyy-MM-dd")
            room_id = self.room_selector.currentData()

            # Условие для фильтрации по номеру
            room_condition = f"AND r.id_room = {room_id}" if room_id else ""

            # 1. Выручка
            query = f"""
            SELECT COALESCE(SUM(p.amount), 0) AS revenue
            FROM payment p
            JOIN reservation r ON p.id_reservation = r.id
            WHERE p.date_of_payment BETWEEN %s AND %s
            {room_condition}
            """
            result = self.db_manager.execute_query(query, (start_date, end_date), fetch=True)
            revenue = float(result[0]['revenue'])
            self.revenue_label.setText(f"{revenue:.2f} руб.")

            # 2. Количество бронирований
            query = f"""
            SELECT COUNT(*) AS count
            FROM reservation r
            WHERE r.check_in_time BETWEEN %s AND %s
            {room_condition}
            """
            result = self.db_manager.execute_query(query, (start_date, end_date), fetch=True)
            bookings_count = result[0]['count']
            self.bookings_label.setText(str(bookings_count))

            # 3. Загрузка номеров
            if room_id:
                query = """
                SELECT 
                    (SUM(EXTRACT(DAY FROM (LEAST(check_out_time, %s::timestamp) - GREATEST(check_in_time, %s::timestamp)))) * 100.0 / 
                    (EXTRACT(DAY FROM (%s::timestamp - %s::timestamp)) + 1)) AS occupancy
                FROM reservation
                WHERE id_room = %s
                AND check_in_time <= %s AND check_out_time >= %s
                """
                result = self.db_manager.execute_query(
                    query,
                    (end_date, start_date, end_date, start_date, room_id, end_date, start_date),
                    fetch=True
                )
            else:
                query = """
                SELECT 
                    (SUM(EXTRACT(DAY FROM (LEAST(check_out_time, %s::timestamp) - GREATEST(check_in_time, %s::timestamp)))) * 100.0 / 
                    ((SELECT COUNT(*) FROM room) * (EXTRACT(DAY FROM (%s::timestamp - %s::timestamp)) + 1))) AS occupancy
                FROM reservation
                WHERE check_in_time <= %s AND check_out_time >= %s
                """
                result = self.db_manager.execute_query(
                    query,
                    (end_date, start_date, end_date, start_date, end_date, start_date),
                    fetch=True
                )

            occupancy = float(result[0]['occupancy'] or 0)
            self.occupancy_label.setText(f"{occupancy:.2f}%")

            # 4. ADR
            if room_id:
                query = """
                SELECT 
                    CASE WHEN SUM(EXTRACT(DAY FROM (r.check_out_time - r.check_in_time))) > 0 
                    THEN SUM(p.amount) / SUM(EXTRACT(DAY FROM (r.check_out_time - r.check_in_time)))
                    ELSE 0 END AS adr
                FROM reservation r
                JOIN payment p ON r.id = p.id_reservation
                WHERE r.id_room = %s
                AND r.check_in_time <= %s AND r.check_out_time >= %s
                """
                result = self.db_manager.execute_query(
                    query,
                    (room_id, end_date, start_date),
                    fetch=True
                )
            else:
                query = """
                SELECT 
                    CASE WHEN SUM(EXTRACT(DAY FROM (r.check_out_time - r.check_in_time))) > 0 
                    THEN SUM(p.amount) / SUM(EXTRACT(DAY FROM (r.check_out_time - r.check_in_time)))
                    ELSE 0 END AS adr
                FROM reservation r
                JOIN payment p ON r.id = p.id_reservation
                WHERE r.check_in_time <= %s AND r.check_out_time >= %s
                """
                result = self.db_manager.execute_query(
                    query,
                    (end_date, start_date),
                    fetch=True
                )

            adr = result[0]['adr'] or 0
            self.adr_label.setText(f"{adr:.2f} руб.")

            # 5. RevPAR
            revpar = adr * (occupancy / 100)
            self.revpar_label.setText(f"{revpar:.2f} руб.")

            # 6. Список бронирований
            if room_id:
                query = """
                SELECT 
                    g.surname || ' ' || g.name AS guest_name,
                    r.check_in_time,
                    r.check_out_time,
                    EXTRACT(DAY FROM (r.check_out_time - r.check_in_time)) AS nights,
                    p.amount AS booking_cost,
                    COALESCE((
                        SELECT SUM(s.price) 
                        FROM service_for_guest sfg 
                        JOIN service s ON sfg.id_service = s.id 
                        WHERE sfg.id_guest = g.id AND sfg.date BETWEEN r.check_in_time AND r.check_out_time
                    ), 0) AS services_cost
                FROM reservation r
                JOIN guest g ON r.id_guest = g.id
                JOIN payment p ON r.id = p.id_reservation
                WHERE r.id_room = %s
                AND r.check_in_time <= %s AND r.check_out_time >= %s
                ORDER BY r.check_in_time DESC
                """
                bookings = self.db_manager.execute_query(
                    query,
                    (room_id, end_date, start_date),
                    fetch=True
                )
            else:
                query = """
                SELECT 
                    g.surname || ' ' || g.name AS guest_name,
                    r.check_in_time,
                    r.check_out_time,
                    EXTRACT(DAY FROM (r.check_out_time - r.check_in_time)) AS nights,
                    p.amount AS booking_cost,
                    COALESCE((
                        SELECT SUM(s.price) 
                        FROM service_for_guest sfg 
                        JOIN service s ON sfg.id_service = s.id 
                        WHERE sfg.id_guest = g.id AND sfg.date BETWEEN r.check_in_time AND r.check_out_time
                    ), 0) AS services_cost
                FROM reservation r
                JOIN guest g ON r.id_guest = g.id
                JOIN payment p ON r.id = p.id_reservation
                WHERE r.check_in_time <= %s AND r.check_out_time >= %s
                ORDER BY r.check_in_time DESC
                LIMIT 100
                """
                bookings = self.db_manager.execute_query(
                    query,
                    (end_date, start_date),
                    fetch=True
                )

            # Заполняем таблицу бронирований
            self.bookings_table.setRowCount(len(bookings))
            for row, booking in enumerate(bookings):
                self.bookings_table.setItem(row, 0, QTableWidgetItem(booking['guest_name']))

                # Форматируем даты
                check_in = booking['check_in_time'].strftime("%d.%m.%Y") if booking['check_in_time'] else ""
                check_out = booking['check_out_time'].strftime("%d.%m.%Y") if booking['check_out_time'] else ""

                self.bookings_table.setItem(row, 1, QTableWidgetItem(check_in))
                self.bookings_table.setItem(row, 2, QTableWidgetItem(check_out))
                self.bookings_table.setItem(row, 3, QTableWidgetItem(str(int(booking['nights']))))
                self.bookings_table.setItem(row, 4, QTableWidgetItem(f"{booking['booking_cost']:.2f} руб."))
                self.bookings_table.setItem(row, 5, QTableWidgetItem(f"{booking['services_cost']:.2f} руб."))

                # Выделяем цветом бронирования с доп. услугами
                if booking['services_cost'] > 0:
                    for col in range(6):
                        item = self.bookings_table.item(row, col)
                        item.setBackground(QColor(230, 255, 230))

            if not bookings:
                QMessageBox.information(self, "Информация", "За выбранный период нет бронирований")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сформировать отчет: {str(e)}")

    def update_services_table(self):
        """Обновляет таблицу доступных услуг"""
        self.services_table.setRowCount(0)

        try:
            query = "SELECT id, title, price FROM service ORDER BY title"
            services = self.db_manager.execute_query(query, fetch=True)

            # Заполняем таблицу
            for row, service in enumerate(services):
                self.services_table.insertRow(row)

                # Получаем данные в зависимости от типа результата
                if isinstance(service, dict):
                    service_id = service['id']
                    title = service['title']
                    price = service['price']
                else:
                    service_id = service[0]
                    title = service[1]
                    price = service[2]

                self.services_table.setItem(row, 0, QTableWidgetItem(title))
                self.services_table.setItem(row, 1, QTableWidgetItem(f"{price:.2f}"))
                self.services_table.setItem(row, 2, QTableWidgetItem(str(service_id)))

            # Подгоняем ширину столбцов под содержимое
            self.services_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список услуг: {str(e)}")

    def delete_service_from_list(self):
        """Удаляет выбранную услугу из списка"""
        selected_row = self.services_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите услугу для удаления")
            return

        # Получаем данные из таблицы
        title = self.services_table.item(selected_row, 0).text()
        service_id = self.services_table.item(selected_row, 2).text()

        # Подтверждение удаления
        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить услугу '{title}'?\n"
                                     f"Это также удалит все связанные записи об оказании этой услуги постояльцам.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.No:
            return

        try:
            # Удаляем услугу из базы данных
            query = "DELETE FROM service WHERE id = %s"
            self.db_manager.execute_query(query, params=(service_id,))

            QMessageBox.information(self, "Успех", "Услуга успешно удалена")

            # Если был режим редактирования этой услуги, сбрасываем его
            if self.service_edit_id == service_id:
                self.service_edit_id = None
                self.add_service_to_list_button.setText("Добавить")
                self.edit_service_button.setText("Редактировать выбранную")
                self.service_title_input.clear()
                self.service_price_input.setValue(0.0)

            # Обновляем таблицу услуг и комбобокс
            self.update_services_table()
            self.update_services_combobox()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить услугу: {str(e)}")

    def edit_service(self):
        """Редактирует выбранную услугу или загружает её данные для редактирования"""
        selected_row = self.services_table.currentRow()

        # Если есть ID редактируемой услуги, значит мы в режиме сохранения изменений
        if self.service_edit_id is not None:
            title = self.service_title_input.text().strip()
            price = self.service_price_input.value()

            if not title:
                QMessageBox.warning(self, "Предупреждение", "Введите название услуги")
                return

            try:
                # Обновляем данные услуги в базе
                query = "UPDATE service SET title = %s, price = %s WHERE id = %s"
                self.db_manager.execute_query(query, params=(title, price, self.service_edit_id))

                QMessageBox.information(self, "Успех", "Услуга успешно обновлена")

                # Сбрасываем режим редактирования
                self.service_edit_id = None
                self.add_service_to_list_button.setText("Добавить")
                self.edit_service_button.setText("Редактировать выбранную")

                # Очищаем поля ввода
                self.service_title_input.clear()
                self.service_price_input.setValue(0.0)

                # Обновляем таблицу услуг и комбобокс
                self.update_services_table()
                self.update_services_combobox()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось обновить услугу: {str(e)}")
        else:
            # Загружаем данные выбранной услуги для редактирования
            if selected_row < 0:
                QMessageBox.warning(self, "Предупреждение", "Выберите услугу для редактирования")
                return

            # Получаем данные из таблицы
            title = self.services_table.item(selected_row, 0).text()
            price_text = self.services_table.item(selected_row, 1).text().replace(" руб.", "")
            service_id = self.services_table.item(selected_row, 2).text()

            # Заполняем поля формы
            self.service_title_input.setText(title)
            self.service_price_input.setValue(float(price_text))

            # Запоминаем ID редактируемой услуги и меняем текст кнопок
            self.service_edit_id = service_id
            self.add_service_to_list_button.setText("Отмена")
            self.edit_service_button.setText("Сохранить изменения")

    def add_service_to_list(self):
        """Добавляет новую услугу в список или отменяет редактирование"""
        # Если мы в режиме редактирования и нажали "Отмена"
        if self.service_edit_id is not None and self.add_service_to_list_button.text() == "Отмена":
            # Сбрасываем режим редактирования
            self.service_edit_id = None
            self.add_service_to_list_button.setText("Добавить")
            self.edit_service_button.setText("Редактировать выбранную")

            # Очищаем поля ввода
            self.service_title_input.clear()
            self.service_price_input.setValue(0.0)
            return

        # Обычный режим добавления новой услуги
        title = self.service_title_input.text().strip()
        price = self.service_price_input.value()

        if not title:
            QMessageBox.warning(self, "Предупреждение", "Введите название услуги")
            return

        try:
            # Добавляем новую услугу в базу данных
            query = "INSERT INTO service (title, price) VALUES (%s, %s)"
            self.db_manager.execute_query(query, params=(title, price))

            QMessageBox.information(self, "Успех", "Услуга успешно добавлена")

            # Очищаем поля ввода
            self.service_title_input.clear()
            self.service_price_input.setValue(0.0)

            # Обновляем таблицу услуг и комбобокс
            self.update_services_table()
            self.update_services_combobox()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить услугу: {str(e)}")

    def update_services_combobox(self):
        """Обновляет список доступных услуг в комбобоксе"""
        self.service_combobox.clear()

        try:
            # Используем метод execute_query из DatabaseManager
            query = "SELECT id, title, price FROM service ORDER BY title"
            services = self.db_manager.execute_query(query, fetch=True)

            if services:
                for service in services:
                    # Т.к. используется DictCursor, результаты будут в виде словарей
                    service_id = service['id']
                    title = service['title']
                    price = service['price']

                    self.service_combobox.addItem(f"{title} ({price} руб.)", service_id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список услуг: {str(e)}")

    def update_guest_services_table(self):
        """Обновляет таблицу услуг выбранного постояльца"""
        self.guest_services_table.setRowCount(0)

        # Получаем ID выбранного постояльца
        guest_id = self.service_guest_combobox.currentData()
        if guest_id is None:
            return

        # Обновляем заголовок таблицы
        guest_name = self.service_guest_combobox.currentText()
        self.guest_services_label.setText(f"Услуги постояльца: {guest_name}")

        try:
            # Запрос услуг постояльца
            query = """
            SELECT sfg.id, s.title, s.price, sfg.date 
            FROM service_for_guest sfg
            JOIN service s ON sfg.id_service = s.id
            WHERE sfg.id_guest = %s
            ORDER BY sfg.date DESC
            """
            services = self.db_manager.execute_query(query, params=(guest_id,), fetch=True)

            # Заполняем таблицу
            for row, service in enumerate(services):
                self.guest_services_table.insertRow(row)

                # Поскольку db_manager использует DictCursor, доступ к полям по имени
                self.guest_services_table.setItem(row, 0, QTableWidgetItem(service['title']))
                self.guest_services_table.setItem(row, 1, QTableWidgetItem(f"{service['price']} руб."))

                # Форматируем дату и время
                date_time = service['date'].strftime("%d.%m.%Y %H:%M") if service['date'] else "-"
                self.guest_services_table.setItem(row, 2, QTableWidgetItem(date_time))

                # Сохраняем ID услуги в скрытой колонке
                self.guest_services_table.setItem(row, 3, QTableWidgetItem(str(service['id'])))

            # Подгоняем ширину столбцов под содержимое
            self.guest_services_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить услуги постояльца: {str(e)}")

    def add_service_for_guest(self):
        """Добавляет выбранную услугу выбранному постояльцу"""
        # Получаем ID выбранного постояльца и услуги
        guest_id = self.service_guest_combobox.currentData()
        service_id = self.service_combobox.currentData()

        if guest_id is None:
            QMessageBox.warning(self, "Предупреждение", "Выберите постояльца")
            return

        if service_id is None:
            QMessageBox.warning(self, "Предупреждение", "Выберите услугу")
            return

        # Получаем название услуги для проверки, является ли она уборкой
        service_name = self.service_combobox.currentText().split(" (")[0].lower()

        # Получаем дату и время
        service_date = self.service_date.dateTime().toPyDateTime()

        # Проверяем, есть ли у постояльца активное проживание на указанную дату
        try:
            query = """
            SELECT r.id, r.floor, r.number, r.category
            FROM reservation b
            JOIN room r ON b.id_room = r.id
            WHERE b.id_guest = %s 
              AND b.check_in_time <= %s 
              AND b.check_out_time >= %s
            LIMIT 1
            """
            rooms = self.db_manager.execute_query(
                query,
                params=(guest_id, service_date, service_date),
                fetch=True
            )

            if not rooms:
                QMessageBox.warning(self, "Предупреждение",
                                    "У этого постояльца нет активного проживания на указанную дату")
                return

            # Берем первую комнату (должна быть только одна из-за LIMIT 1)
            room = rooms[0]
            room_id = room['id']
            room_info = f"Этаж {room['floor']}, Номер {room['number']} ({room['category']})"

            # Если услуга связана с уборкой, открываем диалог выбора сотрудника
            employee_id = None
            if "уборк" in service_name or "чистк" in service_name or "убират" in service_name:
                # Создаем диалог для выбора сотрудника
                dialog = QDialog(self)
                dialog.setWindowTitle("Выбор сотрудника для уборки")
                dialog.setMinimumWidth(400)

                layout = QVBoxLayout(dialog)

                # Информация о комнате
                room_label = QLabel(f"Комната: {room_info}")
                layout.addWidget(room_label)

                # Выбор сотрудника
                employee_layout = QFormLayout()
                employee_combobox = QComboBox()

                try:
                    # Получаем список сотрудников
                    query = """
                    SELECT id, name, surname
                    FROM employee
                    ORDER BY surname, name
                    """
                    employees = self.db_manager.execute_query(query, fetch=True)

                    if employees:
                        for employee in employees:
                            display_text = f"{employee['surname']} {employee['name']}"
                            employee_combobox.addItem(display_text, employee['id'])
                    else:
                        QMessageBox.warning(self, "Предупреждение", "Нет доступных сотрудников для уборки")
                        return
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список сотрудников: {str(e)}")
                    return

                employee_layout.addRow("Сотрудник:", employee_combobox)
                layout.addLayout(employee_layout)

                # Кнопки
                buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                buttons.accepted.connect(dialog.accept)
                buttons.rejected.connect(dialog.reject)
                layout.addWidget(buttons)

                # Показываем диалог
                if dialog.exec_() == QDialog.Accepted:
                    employee_id = employee_combobox.currentData()

                    # Добавляем запись об уборке
                    try:
                        query = """
                        INSERT INTO clear (id_employee, id_room, date)
                        VALUES (%s, %s, %s)
                        """
                        self.db_manager.execute_query(
                            query,
                            params=(employee_id, room_id, service_date)
                        )
                    except Exception as e:
                        QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись об уборке: {str(e)}")
                        return
                else:
                    # Пользователь отменил операцию
                    return
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить данные о проживании: {str(e)}")
            return

        # Добавляем услугу для постояльца
        try:
            query = """
            INSERT INTO service_for_guest (id_guest, id_service, date)
            VALUES (%s, %s, %s)
            """
            self.db_manager.execute_query(query, params=(guest_id, service_id, service_date))

            QMessageBox.information(self, "Успех", "Услуга успешно добавлена")

            # Обновляем таблицу услуг
            self.update_guest_services_table()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить услугу: {str(e)}")

    def delete_service_for_guest(self):
        """Удаляет выбранную услугу постояльца"""
        # Получаем выбранную строку
        selected_row = self.guest_services_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите услугу для удаления")
            return

        # Получаем ID услуги из скрытой колонки
        service_id = self.guest_services_table.item(selected_row, 3).text()

        # Подтверждение удаления
        service_name = self.guest_services_table.item(selected_row, 0).text()
        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить услугу '{service_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.No:
            return

        try:
            # Используем метод execute_query из DatabaseManager
            query = "DELETE FROM service_for_guest WHERE id = %s"
            self.db_manager.execute_query(query, params=(service_id,))

            QMessageBox.information(self, "Успех", "Услуга успешно удалена")

            # Обновляем таблицу услуг
            self.update_guest_services_table()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить услугу: {str(e)}")

    def show_change_password_dialog(self):
        self.password_change_window = PasswordChangeWindow(self.db_manager, self.user['id'])
        self.password_change_window.show()

    def add_guest(self):
        name = self.name_input.text()
        surname = self.surname_input.text()
        patronymic = self.patronymic_input.text() or None

        # Проверяем, ввел ли пользователь мобильный телефон
        mobile_text = self.mobile_input.text()
        mobile = int(mobile_text) if mobile_text else None

        passport_text = self.passport_input.text()

        # Валидация данных
        if not name or not surname or not passport_text:
            QMessageBox.warning(self, "Ошибка", "Имя, фамилия и паспорт обязательны для заполнения")
            return

        try:
            passport = int(passport_text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Паспорт должен содержать только цифры")
            return

        # Добавление гостя в базу данных
        try:
            query = """
            INSERT INTO guest (name, surname, patronymic, mobile, passport)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """
            result = self.db_manager.execute_query(query, (name, surname, patronymic, mobile, passport), fetch=True)

            if result:
                QMessageBox.information(self, "Успех", "Постоялец успешно добавлен")
                # Очистить поля формы
                self.name_input.clear()
                self.surname_input.clear()
                self.patronymic_input.clear()
                self.mobile_input.clear()
                self.passport_input.clear()

                # Обновить список гостей в комбобоксе
                self.update_guest_combobox()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось добавить постояльца")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при добавлении постояльца: {str(e)}")


    def show_room_selection(self):
        # Проверяем, выбран ли гость
        if self.guest_combobox.count() == 0:
            QMessageBox.warning(self, "Ошибка", "Нет доступных постояльцев. Сначала добавьте постояльца.")
            return

        # Проверяем даты
        check_in = self.check_in_date.dateTime().toPyDateTime()
        check_out = self.check_out_date.dateTime().toPyDateTime()

        if check_in >= check_out:
            QMessageBox.warning(self, "Ошибка", "Дата выселения должна быть позже даты заселения")
            return

        # Сохраняем данные для бронирования
        self.current_guest_id = self.guest_combobox.currentData()
        self.current_check_in = check_in
        self.current_check_out = check_out

        # Обновляем таблицу комнат с учетом выбранных дат
        self.update_rooms_table()

        # Переключаемся на вкладку с комнатами
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            tab_widget.setCurrentIndex(2)  # Индекс вкладки "Комнаты"

    def update_rooms_table(self):
        try:
            # Очистить таблицу
            self.rooms_table.setRowCount(0)

            # Увеличиваем количество столбцов до 5 (добавляем столбец стоимости)
            self.rooms_table.setColumnCount(5)
            self.rooms_table.setHorizontalHeaderLabels(["Этаж", "Номер", "Категория", "Стоимость", "ID"])

            query = """
                    SELECT id, floor, number, category, cost
                    FROM room 
                    ORDER BY floor, number
                    """
            rooms = self.db_manager.execute_query(query, fetch=True)

            # Заполнить таблицу
            for row, room in enumerate(rooms):
                self.rooms_table.insertRow(row)

                # Заполняем ячейки таблицы
                self.rooms_table.setItem(row, 0, QTableWidgetItem(str(room['floor'])))
                self.rooms_table.setItem(row, 1, QTableWidgetItem(str(room['number'])))
                self.rooms_table.setItem(row, 2, QTableWidgetItem(room['category']))

                # Добавляем столбец стоимости
                self.rooms_table.setItem(row, 3, QTableWidgetItem(str(room['cost'])))

                # Сохраняем ID комнаты в скрытых данных
                self.rooms_table.setItem(row, 4, QTableWidgetItem(str(room['id'])))

            # Скрыть колонку с ID
            self.rooms_table.setColumnHidden(4, True)

            # Растянуть колонки по содержимому
            self.rooms_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список комнат: {str(e)}")

    def find_available_rooms(self):
        # Проверяем, выбран ли гость
        if self.guest_combobox.count() == 0:
            QMessageBox.warning(self, "Ошибка", "Нет доступных постояльцев. Сначала добавьте постояльца.")
            return

        # Получаем выбранного гостя
        self.current_guest_id = self.guest_combobox.currentData()

        # Получаем даты заселения и выселения
        check_in = self.check_in_date.dateTime().toPyDateTime()
        check_out = self.check_out_date.dateTime().toPyDateTime()
        print(check_in, check_out)

        # Проверяем корректность дат
        if check_in >= check_out:
            QMessageBox.warning(self, "Ошибка", "Дата выселения должна быть позже даты заселения")
            return

        # Сохраняем даты для использования при бронировании
        self.current_check_in = check_in
        self.current_check_out = check_out

        # Обновляем таблицу комнат с учетом выбранных дат
        try:
            # Очистить таблицу
            self.rooms_table.setRowCount(0)

            # Увеличиваем количество столбцов до 5 (добавляем столбец стоимости)
            self.rooms_table.setColumnCount(5)
            self.rooms_table.setHorizontalHeaderLabels(["Этаж", "Номер", "Категория", "Стоимость", "ID"])

            # Получаем список комнат, которые не заняты в выбранный период
            query = """
            SELECT r.id, r.floor, r.number, r.category, r.cost
            FROM room r
            WHERE NOT EXISTS (
                SELECT 1 FROM reservation res
                WHERE res.id_room = r.id
                AND res.status = 'активно'
                AND (
                    (%s >= res.check_in_time AND %s <= res.check_out_time) OR
                    (res.check_in_time >= %s AND res.check_out_time <= %s) OR
                    (%s < res.check_out_time AND %s > res.check_in_time)
                )
            )
            ORDER BY r.floor, r.number
            """

            rooms = self.db_manager.execute_query(
                query,
                (check_in, check_out,
                 check_in, check_out,
                 check_in, check_out),
                fetch=True
            )

            # Заполняем таблицу доступными комнатами
            for row, room in enumerate(rooms):
                self.rooms_table.insertRow(row)

                # Заполняем ячейки таблицы
                self.rooms_table.setItem(row, 0, QTableWidgetItem(str(room['floor'])))
                self.rooms_table.setItem(row, 1, QTableWidgetItem(str(room['number'])))
                self.rooms_table.setItem(row, 2, QTableWidgetItem(room['category']))

                # Добавляем столбец стоимости
                self.rooms_table.setItem(row, 3, QTableWidgetItem(str(room['cost'])))

                # Сохраняем ID комнаты в скрытом столбце
                self.rooms_table.setItem(row, 4, QTableWidgetItem(str(room['id'])))

            # Растянуть колонки по содержимому
            self.rooms_table.resizeColumnsToContents()

            # Показываем сообщение о результатах поиска
            if self.rooms_table.rowCount() == 0:
                QMessageBox.information(self, "Результаты поиска", "Нет доступных комнат на выбранные даты")
            else:
                QMessageBox.information(self, "Результаты поиска",
                                        f"Найдено {self.rooms_table.rowCount()} доступных комнат")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось найти доступные комнаты: {str(e)}")

    def book_room(self):
        try:
            # Проверяем, выбрана ли комната
            selected_rows = self.rooms_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "Ошибка", "Выберите комнату для бронирования")
                return

            # Проверяем, заполнены ли данные для бронирования
            if self.current_guest_id is None or not hasattr(self, 'current_check_in') or not hasattr(self,
                                                                                                     'current_check_out'):
                QMessageBox.warning(self, "Ошибка", "Сначала выполните поиск доступных комнат")
                return

            # Получаем данные выбранной комнаты
            row = selected_rows[0].row()

            # Проверяем наличие элементов
            room_id_item = self.rooms_table.item(row, 4)  # Используем колонку 4 для ID комнаты
            if not room_id_item:
                QMessageBox.warning(self, "Ошибка", "Не удалось получить ID комнаты")
                return

            # Получаем ID и стоимость комнаты
            room_id = int(room_id_item.text())
            room_cost_item = self.rooms_table.item(row, 3)
            room_cost = float(room_cost_item.text())

            # Получаем категорию комнаты для определения количества мест
            room_category = self.rooms_table.item(row, 2).text()  # Используем колонку 2 для категории

            room_capacity = 1

            if ("2х" in room_category or "2-х" in room_category or "двух" in room_category.lower()
                or "2-местный" in room_category.lower() or "двухместный" in room_category.lower()):
                room_capacity = 2
            elif ("3х" in room_category or "3-х" in room_category or "трех" in room_category.lower()
                or "3-местный" in room_category.lower() or "трехместный" in room_category.lower()):
                room_capacity = 3
            elif ("4х" in room_category or "4-х" in room_category or "четырех" in room_category.lower()
                or "4-местный" in room_category.lower() or "четырехместный" in room_category.lower()):
                room_capacity = 4

            # Рассчитываем количество дней
            check_in = self.check_in_date.dateTime().toPyDateTime()
            check_out = self.check_out_date.dateTime().toPyDateTime()
            days = (check_out - check_in).days
            total_cost = room_cost * days

            # Если номер многоместный, спрашиваем о дополнительных гостях
            additional_guests = []
            if room_capacity > 1:
                additional_guests_response = QMessageBox.question(
                    self,
                    "Многоместный номер",
                    f"Номер рассчитан на {room_capacity} человек. Хотите заселить дополнительных гостей?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )

                if additional_guests_response == QMessageBox.Cancel:
                    return

                if additional_guests_response == QMessageBox.Yes:
                    # Запрашиваем дополнительных гостей
                    for i in range(room_capacity - 1):
                        # Создаем диалог для выбора дополнительного гостя
                        additional_guest_dialog = QDialog(self)
                        additional_guest_dialog.setWindowTitle(f"Выбор дополнительного гостя {i + 1}")
                        dialog_layout = QVBoxLayout()

                        # Комбобокс с гостями
                        guest_label = QLabel(f"Выберите гостя {i + 1}:")
                        guest_combo = QComboBox()

                        # Заполняем комбобокс гостями (кроме уже выбранных)
                        query = """
                        SELECT id, surname, name, patronymic
                        FROM guest
                        WHERE id != %s
                        """
                        params = [self.current_guest_id]

                        # Добавляем идентификаторы уже выбранных дополнительных гостей
                        for guest_id in additional_guests:
                            params.append(guest_id)

                        # Строим IN-часть запроса
                        in_clause = " AND ".join(["id != %s" for _ in range(len(params))])
                        if in_clause:
                            query += f" AND {in_clause}"

                        query += " ORDER BY surname, name"

                        guests = self.db_manager.execute_query(query, tuple(params), fetch=True)

                        for guest in guests:
                            full_name = f"{guest['surname']} {guest['name']}"
                            if guest['patronymic']:
                                full_name += f" {guest['patronymic']}"
                            guest_combo.addItem(full_name, guest['id'])

                        # Опция добавления нового гостя
                        guest_combo.addItem("+ Добавить нового гостя", -1)

                        dialog_layout.addWidget(guest_label)
                        dialog_layout.addWidget(guest_combo)

                        # Кнопки
                        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                        button_box.accepted.connect(additional_guest_dialog.accept)
                        button_box.rejected.connect(additional_guest_dialog.reject)
                        dialog_layout.addWidget(button_box)

                        additional_guest_dialog.setLayout(dialog_layout)

                        # Обработка результата диалога
                        if additional_guest_dialog.exec_() == QDialog.Accepted:
                            selected_guest_id = guest_combo.currentData()

                            # Если выбрано "Добавить нового гостя"
                            if selected_guest_id == -1:
                                # Здесь можно открыть форму добавления гостя
                                # Для простоты, просто показываем сообщение
                                QMessageBox.information(self, "Информация",
                                                        "Для добавления нового гостя используйте вкладку 'Добавление постояльца'")
                                return

                            additional_guests.append(selected_guest_id)
                        else:
                            # Пользователь отменил выбор дополнительного гостя
                            break

            # Создаем диалог подтверждения оплаты
            payment_dialog = QDialog(self)
            payment_dialog.setWindowTitle("Подтверждение бронирования")
            payment_layout = QVBoxLayout()

            # Информация о бронировании
            info_text = f"Детали бронирования:\n" \
                        f"Комната: {self.rooms_table.item(row, 1).text()}\n" \
                        f"Категория: {room_category}\n" \
                        f"Вместимость: {room_capacity} человек\n" \
                        f"Заезд: {check_in.strftime('%d.%m.%Y %H:%M')}\n" \
                        f"Выезд: {check_out.strftime('%d.%m.%Y %H:%M')}\n" \
                        f"Количество дней: {days}\n" \
                        f"Стоимость за сутки: {room_cost} руб.\n" \
                        f"Итого к оплате: {total_cost} руб.\n"

            # Добавляем информацию о гостях
            info_text += f"\nОсновной гость: {self.guest_combobox.currentText()}\n"

            if additional_guests:
                info_text += "Дополнительные гости:\n"
                for i, guest_id in enumerate(additional_guests):
                    # Получаем информацию о госте
                    guest_query = "SELECT surname, name, patronymic FROM guest WHERE id = %s"
                    guest_info = self.db_manager.execute_query(guest_query, (guest_id,), fetch=True)[0]

                    full_name = f"{guest_info['surname']} {guest_info['name']}"
                    if guest_info['patronymic']:
                        full_name += f" {guest_info['patronymic']}"

                    info_text += f"{i + 1}. {full_name}\n"

            info_label = QLabel(info_text)
            payment_layout.addWidget(info_label)

            # Выбор метода оплаты
            payment_method_layout = QHBoxLayout()
            payment_method_label = QLabel("Метод оплаты:")
            payment_method_combo = QComboBox()
            payment_method_combo.addItems(["Наличный", "Банковская карта"])
            payment_method_layout.addWidget(payment_method_label)
            payment_method_layout.addWidget(payment_method_combo)
            payment_layout.addLayout(payment_method_layout)

            # Кнопки
            button_layout = QHBoxLayout()
            confirm_button = QPushButton("Подтвердить")
            cancel_button = QPushButton("Отмена")
            button_layout.addWidget(confirm_button)
            button_layout.addWidget(cancel_button)
            payment_layout.addLayout(button_layout)

            payment_dialog.setLayout(payment_layout)

            # Обработчики кнопок
            def on_confirm():
                try:
                    # Создаем новое бронирование для основного гостя
                    query_reservation = """
                            INSERT INTO reservation (id_room, id_guest, check_in_time, check_out_time, status)
                            VALUES (%s, %s, %s, %s, 'активно')
                            RETURNING id
                            """
                    result_reservation = self.db_manager.execute_query(
                        query_reservation,
                        (room_id, self.current_guest_id, check_in, check_out),
                        fetch=True
                    )

                    # Обновляем статус номера на "Занят"
                    update_room_status_query = """
                                UPDATE room SET status = 'Занят' WHERE id = %s
                            """
                    self.db_manager.execute_query(update_room_status_query, (room_id,))

                    if result_reservation:
                        reservation_id = result_reservation[0]['id']

                        # Создаем запись об оплате
                        query_payment = """
                                INSERT INTO payment (date_of_payment, amount, payment_method, id_reservation)
                                VALUES (%s, %s, %s, %s)
                                """
                        self.db_manager.execute_query(
                            query_payment,
                            (datetime.datetime.now(), total_cost,
                             payment_method_combo.currentText(),
                             reservation_id)
                        )

                        # Добавляем бронирования для дополнительных гостей
                        for guest_id in additional_guests:
                            additional_query = """
                                    INSERT INTO reservation (id_room, id_guest, check_in_time, check_out_time, status)
                                    VALUES (%s, %s, %s, %s, 'активно')
                                    """
                            self.db_manager.execute_query(
                                additional_query,
                                (room_id, guest_id, check_in, check_out)
                            )

                        # Обновляем список доступных комнат
                        self.find_available_rooms()

                        QMessageBox.information(self, "Успех", "Бронирование и оплата успешно созданы")
                        payment_dialog.accept()

                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при бронировании: {str(e)}")

            def on_cancel():
                payment_dialog.reject()

            confirm_button.clicked.connect(on_confirm)
            cancel_button.clicked.connect(on_cancel)

            # Показываем диалог
            payment_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")

    def update_guest_combobox(self, combobox=None):
        if combobox is None:
            combobox = self.guest_combobox

        combobox.clear()

        try:
            # Получить всех гостей из базы данных через db_manager
            query = """
                    SELECT id, name, surname, patronymic, passport 
                    FROM guest 
                    ORDER BY surname, name
                    """
            guests = self.db_manager.execute_query(query, fetch=True)

            # Заполнить комбобокс
            if guests:
                for guest in guests:
                    # Формируем строку для отображения
                    patronymic_str = f" {guest['patronymic']}" if guest['patronymic'] else ""
                    display_text = f"{guest['surname']} {guest['name']}{patronymic_str} (паспорт: {guest['passport']})"

                    # Сохраняем ID гостя в userData
                    combobox.addItem(display_text, guest['id'])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список постояльцев: {str(e)}")

    def update_rooms_table(self):
        try:
            # Очистить таблицу
            self.rooms_table.setRowCount(0)

            # Получить все комнаты из базы данных
            query = """
                    SELECT id, floor, number, category, status, cost 
                    FROM room 
                    ORDER BY floor, number
                    """
            rooms = self.db_manager.execute_query(query, fetch=True)

            # Заполнить таблицу
            for row, room in enumerate(rooms):
                self.rooms_table.insertRow(row)

                # Заполняем ячейки таблицы
                self.rooms_table.setItem(row, 0, QTableWidgetItem(str(room['floor'])))
                self.rooms_table.setItem(row, 1, QTableWidgetItem(str(room['number'])))
                self.rooms_table.setItem(row, 2, QTableWidgetItem(room['category']))

                self.rooms_table.setItem(row, 3, QTableWidgetItem(str(room['cost'])))

                # Сохраняем ID комнаты в скрытом столбце
                self.rooms_table.setItem(row, 4, QTableWidgetItem(str(room['id'])))

            # Растянуть колонки по содержимому
            self.rooms_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список комнат: {str(e)}")

    class PasswordChangeWindow(QDialog):
        def __init__(self, db_manager, user_id):
            super().__init__()
            self.db_manager = db_manager
            self.user_id = user_id
            self.init_ui()

        def init_ui(self):
            self.setWindowTitle('Смена пароля')
            self.setMinimumWidth(300)

            layout = QVBoxLayout()

            # Поля для ввода паролей
            form_layout = QFormLayout()

            self.current_password = QLineEdit()
            self.current_password.setEchoMode(QLineEdit.Password)
            form_layout.addRow("Текущий пароль:", self.current_password)

            self.new_password = QLineEdit()
            self.new_password.setEchoMode(QLineEdit.Password)
            form_layout.addRow("Новый пароль:", self.new_password)

            self.confirm_password = QLineEdit()
            self.confirm_password.setEchoMode(QLineEdit.Password)
            form_layout.addRow("Подтвердите пароль:", self.confirm_password)

            layout.addLayout(form_layout)

            # Кнопки
            buttons_layout = QHBoxLayout()

            self.cancel_button = QPushButton("Отмена")
            self.cancel_button.clicked.connect(self.reject)
            buttons_layout.addWidget(self.cancel_button)

            self.save_button = QPushButton("Сохранить")
            self.save_button.clicked.connect(self.change_password)
            buttons_layout.addWidget(self.save_button)

            layout.addLayout(buttons_layout)

            self.setLayout(layout)

        def change_password(self):
            current_password = self.current_password.text()
            new_password = self.new_password.text()
            confirm_password = self.confirm_password.text()

            # Проверка на пустые поля
            if not current_password or not new_password or not confirm_password:
                QMessageBox.warning(self, "Ошибка", "Все поля должны быть заполнены")
                return

            # Проверка совпадения паролей
            if new_password != confirm_password:
                QMessageBox.warning(self, "Ошибка", "Новый пароль и подтверждение не совпадают")
                return

            try:
                # Проверка текущего пароля
                check_query = """
                SELECT password FROM users WHERE id = %s
                """
                result = self.db_manager.execute_query(check_query, (self.user_id,), fetch=True)

                if not result or not check_password(current_password, result[0]['password']):
                    QMessageBox.warning(self, "Ошибка", "Неверный текущий пароль")
                    return

                # Обновление пароля
                update_query = """
                UPDATE users SET password = %s WHERE id = %s
                """
                self.db_manager.execute_query(update_query, (new_password, self.user_id))

                QMessageBox.information(self, "Успех", "Пароль успешно изменен")
                self.accept()

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при смене пароля: {str(e)}")

# Вспомогательные функции для работы с паролями
def hash_password(password):
    # Здесь должна быть реализация хеширования пароля
    # Например, с использованием bcrypt или другой библиотеки
    return password  # Это просто заглушка

def check_password(password, hashed_password):
    # Здесь должна быть реализация проверки пароля
    # Соответствующая используемому алгоритму хеширования
    return password == hashed_password  # Это просто заглушка
def main():
    app = QApplication(sys.argv)

    # Подключаемся к базе данных
    db_manager = DatabaseManager()

    # Проверяем неактивных пользователей
    blocked_count = db_manager.check_inactive_users()
    if blocked_count > 0:
        print(f"Заблокировано {blocked_count} неактивных пользователей")

    # Запускаем окно авторизации
    login_window = LoginWindow(db_manager)
    login_window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
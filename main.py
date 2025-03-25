import sys
import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QHBoxLayout, QMessageBox, QGridLayout,
                             QTableWidget, QTableWidgetItem, QComboBox, QMainWindow, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
import psycopg2
import hashlib

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
        self.setMinimumSize(600, 400)

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

        # Пустой растягивающийся элемент для выравнивания
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(spacer)

        self.setCentralWidget(central_widget)

    def show_change_password_dialog(self):
        self.password_change_window = PasswordChangeWindow(self.db_manager, self.user['id'])
        self.password_change_window.show()

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
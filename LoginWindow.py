from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QMessageBox, QGridLayout)

import PasswordChangeWindow
from AdminMainWindow import AdminMainWindow
from UserMainWindow import UserMainWindow


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
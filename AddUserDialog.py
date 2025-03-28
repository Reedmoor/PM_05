from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QMessageBox, QGridLayout,
                             QComboBox)


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

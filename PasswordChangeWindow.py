from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QMessageBox, QGridLayout)


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
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton,
                             QVBoxLayout, QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem, QComboBox,
                             QMainWindow)

from AddUserDialog import AddUserDialog


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
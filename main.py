import sys

from PyQt5.QtWidgets import (QApplication)

import DatabaseManager
from LoginWindow import LoginWindow


def main():
    app = QApplication(sys.argv)

    # Подключаемся к базе данных
    db_manager = DatabaseManager.DatabaseManager()

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
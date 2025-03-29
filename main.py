import sys

from PyQt5.QtWidgets import (QApplication)

import DatabaseManager
from LoginWindow import LoginWindow


def main():
    app = QApplication(sys.argv)

    db_manager = DatabaseManager.DatabaseManager()

    blocked_count = db_manager.check_inactive_users()
    if blocked_count > 0:
        print(f"Заблокировано {blocked_count} неактивных пользователей")

    login_window = LoginWindow(db_manager)
    login_window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
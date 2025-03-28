import datetime

from PyQt5.QtCore import Qt, QDateTime, QDate
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QHBoxLayout, QMessageBox, QGridLayout,
                             QTableWidget, QTableWidgetItem, QComboBox, QMainWindow, QTabWidget,
                             QFormLayout, QDateTimeEdit, QDialog, QSplitter, QGroupBox, QDoubleSpinBox,
                             QDialogButtonBox, QHeaderView, QDateEdit)

from PasswordChangeWindow import PasswordChangeWindow


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
            # Создаем диалог для выбора уборщика
            cleaner_dialog = QDialog(self)
            cleaner_dialog.setWindowTitle("Выбор сотрудника для уборки")
            cleaner_dialog.setMinimumWidth(300)
            dialog_layout = QVBoxLayout()

            # Заголовок
            header_label = QLabel("Выберите сотрудника, который выполнил уборку:")
            dialog_layout.addWidget(header_label)

            # Таблица с сотрудниками
            cleaners_table = QTableWidget()
            cleaners_table.setColumnCount(3)
            cleaners_table.setHorizontalHeaderLabels(["ID", "Имя", "Фамилия"])
            cleaners_table.setSelectionBehavior(QTableWidget.SelectRows)
            cleaners_table.setSelectionMode(QTableWidget.SingleSelection)
            cleaners_table.setEditTriggers(QTableWidget.NoEditTriggers)
            cleaners_table.setColumnHidden(0, True)  # Скрываем ID
            cleaners_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            # Получаем список сотрудников из БД
            query = "SELECT id, name, surname FROM public.employee ORDER BY surname, name"
            cleaners = self.db_manager.execute_query(query, fetch=True)

            # Заполняем таблицу
            if cleaners:
                for i, cleaner in enumerate(cleaners):
                    cleaners_table.insertRow(i)

                    # Обработка результата в зависимости от его типа (кортеж или словарь)
                    if isinstance(cleaner, dict):
                        cleaner_id = cleaner['id']
                        name = cleaner['name']
                        surname = cleaner['surname']
                    else:  # Если результат - кортеж
                        cleaner_id = cleaner[0]
                        name = cleaner[1]
                        surname = cleaner[2]

                    cleaners_table.setItem(i, 0, QTableWidgetItem(str(cleaner_id)))
                    cleaners_table.setItem(i, 1, QTableWidgetItem(name))
                    cleaners_table.setItem(i, 2, QTableWidgetItem(surname))

            dialog_layout.addWidget(cleaners_table)

            # Кнопки
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(cleaner_dialog.accept)
            button_box.rejected.connect(cleaner_dialog.reject)
            dialog_layout.addWidget(button_box)

            cleaner_dialog.setLayout(dialog_layout)

            # Показываем диалог и обрабатываем результат
            if cleaner_dialog.exec_() == QDialog.Accepted:
                # Проверяем, выбран ли сотрудник
                selected_rows = cleaners_table.selectionModel().selectedRows()
                if not selected_rows:
                    QMessageBox.warning(self, "Предупреждение", "Сотрудник не выбран")
                    return

                # Получаем ID выбранного сотрудника
                selected_row = selected_rows[0].row()
                cleaner_id_item = cleaners_table.item(selected_row, 0)
                cleaner_id = int(cleaner_id_item.text())

                # Получаем имя и фамилию для отображения в сообщении
                cleaner_name = cleaners_table.item(selected_row, 1).text()
                cleaner_surname = cleaners_table.item(selected_row, 2).text()

                # Обновляем статус номера на "свободный"
                update_query = "UPDATE room SET status = 'свободный' WHERE id = %s"
                self.db_manager.execute_query(update_query, (room_id,))

                # Записываем информацию об уборке (если есть соответствующая таблица)
                try:
                    # Проверяем, существует ли таблица cleaning_log
                    check_table_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'cleaning_log'
                    )
                    """
                    table_exists = self.db_manager.execute_query(check_table_query, fetch=True)

                    # Если таблица существует, добавляем запись
                    if table_exists and table_exists[0][0]:
                        insert_log_query = """
                        INSERT INTO cleaning_log (room_id, employee_id, cleaning_date)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        """
                        self.db_manager.execute_query(insert_log_query, (room_id, cleaner_id))
                except Exception as e:
                    print(f"Ошибка при записи лога уборки: {e}")
                    # Продолжаем выполнение, даже если запись лога не удалась

                # Обновляем список грязных номеров
                self.load_dirty_rooms()

                # Показываем сообщение об успехе
                QMessageBox.information(self, "Успех",
                                        f"Номер отмечен как убранный. Уборку выполнил: {cleaner_name} {cleaner_surname}")

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
            if (self.current_guest_id is None
                    or not hasattr(self, 'current_check_in')
                    or not hasattr(self, 'current_check_out')):
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

            room_capacity_map = {
                ("2", "2х", "2-х", "двух", "2-местный", "двухместный"): 2,
                ("3", "3х", "3-х", "трех", "3-местный", "трехместный"): 3,
                ("4", "4х", "4-х", "четырех", "4-местный", "четырехместный"): 4
            }

            room_capacity = 1
            for keywords, capacity in room_capacity_map.items():
                if any(keyword in room_category.lower() for keyword in keywords):
                    room_capacity = capacity
                    break

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
                    # Создаем диалог для выбора всех дополнительных гостей сразу
                    additional_guests_dialog = QDialog(self)
                    additional_guests_dialog.setWindowTitle(f"Выбор дополнительных гостей")
                    dialog_layout = QVBoxLayout()

                    # Заголовок
                    header_label = QLabel(
                        f"Выберите дополнительных гостей для номера {self.rooms_table.item(row, 1).text()}")
                    dialog_layout.addWidget(header_label)

                    # Создаем список комбобоксов для выбора гостей
                    combo_boxes = []

                    try:
                        # Получаем список всех гостей, кроме основного и тех, кто уже заселен в этот период
                        query = """
                        SELECT g.id, g.surname, g.name, g.patronymic
                        FROM guest g
                        WHERE g.id != %s
                        AND g.id NOT IN (
                            -- Подзапрос для гостей, которые уже заселены в указанный период
                            SELECT r.id_guest 
                            FROM reservation r 
                            WHERE r.status = 'активно'
                            AND (
                                (r.check_in_time <= %s AND r.check_out_time > %s) 
                                OR (r.check_in_time < %s AND r.check_out_time >= %s) 
                                OR (%s <= r.check_in_time AND %s >= r.check_out_time)
                            )
                        )
                        ORDER BY g.surname, g.name
                        """

                        # Параметры для запроса: ID основного гостя, даты заезда и выезда
                        params = (
                            self.current_guest_id,  # ID основного гостя
                            check_out, check_in,  # Проверка на пересечение с заездом
                            check_out, check_in,  # Проверка на пересечение с выездом
                            check_in, check_out  # Проверка на полное включение
                        )

                        # Выполняем запрос
                        available_guests = self.db_manager.execute_query(query, params, fetch=True)

                        # Создаем комбобоксы для каждого дополнительного гостя
                        for i in range(room_capacity - 1):
                            guest_form = QFormLayout()
                            guest_combo = QComboBox()
                            guest_combo.addItem("Выберите гостя...", None)  # Пустой элемент

                            # Заполняем комбобокс доступными гостями
                            if available_guests:
                                for guest in available_guests:
                                    # Обработка результата в зависимости от его типа (кортеж или словарь)
                                    if isinstance(guest, dict):
                                        guest_id = guest['id']
                                        surname = guest['surname']
                                        name = guest['name']
                                        patronymic = guest.get('patronymic', '')
                                    else:  # Если результат - кортеж
                                        guest_id = guest[0]
                                        surname = guest[1]
                                        name = guest[2]
                                        patronymic = guest[3] if len(guest) > 3 and guest[3] else ''

                                    full_name = f"{surname} {name}"
                                    if patronymic:
                                        full_name += f" {patronymic}"

                                    guest_combo.addItem(full_name, guest_id)

                            guest_combo.addItem("+ Добавить нового гостя", -1)
                            combo_boxes.append(guest_combo)

                            guest_form.addRow(f"Гость {i + 1}:", guest_combo)
                            dialog_layout.addLayout(guest_form)

                    except Exception as e:
                        import traceback
                        print(f"Ошибка при получении списка гостей: {e}")
                        print(traceback.format_exc())
                        error_label = QLabel(f"Ошибка при загрузке списка гостей: {str(e)}")
                        dialog_layout.addWidget(error_label)

                    # Кнопки
                    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                    button_box.accepted.connect(additional_guests_dialog.accept)
                    button_box.rejected.connect(additional_guests_dialog.reject)
                    dialog_layout.addWidget(button_box)

                    additional_guests_dialog.setLayout(dialog_layout)

                    # Показываем диалог и обрабатываем результат
                    if additional_guests_dialog.exec_() == QDialog.Accepted:
                        # Собираем ID выбранных гостей
                        for combo in combo_boxes:
                            selected_guest_id = combo.currentData()
                            if selected_guest_id is not None and selected_guest_id != -1:
                                additional_guests.append(selected_guest_id)
                            elif selected_guest_id == -1:
                                # Если выбрано "Добавить нового гостя"
                                QMessageBox.information(self, "Информация",
                                                        "Для добавления нового гостя используйте вкладку 'Добавление постояльца'")
                                return

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
                    try:
                        # Получаем информацию о госте
                        guest_query = "SELECT surname, name, patronymic FROM guest WHERE id = %s"
                        guest_result = self.db_manager.execute_query(guest_query, (guest_id,), fetch=True)
                        if guest_result and len(guest_result) > 0:
                            guest = guest_result[0]

                            # Обработка результата в зависимости от его типа (кортеж или словарь)
                            if isinstance(guest, dict):
                                surname = guest['surname']
                                name = guest['name']
                                patronymic = guest.get('patronymic', '')
                            else:  # Если результат - кортеж
                                surname = guest[0]
                                name = guest[1]
                                patronymic = guest[2] if len(guest) > 2 else ''

                            full_name = f"{surname} {name}"
                            if patronymic:
                                full_name += f" {patronymic}"

                            info_text += f"{i + 1}. {full_name}\n"
                        else:
                            info_text += f"{i + 1}. Гость ID: {guest_id} (информация недоступна)\n"
                    except Exception as e:
                        print(f"Ошибка при получении информации о госте: {e}")
                        info_text += f"{i + 1}. Гость ID: {guest_id} (ошибка получения данных)\n"

                # Создаем и добавляем виджеты ПОСЛЕ завершения цикла
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

                        # Проверяем результат
                        if not result_reservation or len(result_reservation) == 0:
                            QMessageBox.critical(self, "Ошибка", "Не удалось создать бронирование")
                            return

                        # Получаем ID бронирования
                        reservation_id = None
                        if isinstance(result_reservation[0], dict):
                            reservation_id = result_reservation[0].get('id')
                        else:  # Если результат - кортеж
                            reservation_id = result_reservation[0][0] if len(result_reservation[0]) > 0 else None

                        if reservation_id is None:
                            QMessageBox.critical(self, "Ошибка", "Не удалось получить ID бронирования")
                            return

                        # Обновляем статус номера на "Занят"
                        update_room_status_query = """
                                    UPDATE room SET status = 'Занят' WHERE id = %s
                                    """
                        self.db_manager.execute_query(update_room_status_query, (room_id,))

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

                        QMessageBox.information(self, "Успех",
                                                f"Бронирование создано успешно. Заселено гостей: {len(additional_guests) + 1} из {room_capacity}.")
                        payment_dialog.accept()

                    except Exception as e:
                        import traceback
                        print(f"Ошибка при бронировании: {e}")
                        print(traceback.format_exc())  # Выводим полную трассировку ошибки для отладки
                        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при бронировании: {str(e)}")

                def on_cancel():
                    payment_dialog.reject()

            confirm_button.clicked.connect(on_confirm)
            cancel_button.clicked.connect(on_cancel)

                # Показываем диалог
            payment_dialog.exec_()
        except Exception as e:
            print("Обновите список номеров", e)

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
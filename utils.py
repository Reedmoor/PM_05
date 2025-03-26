# utils.py
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt, QDateTime
import psycopg2


def update_services_combobox(combobox, db_config=None, db_manager=None):
    """Обновляет список доступных услуг в комбобоксе"""
    combobox.clear()

    try:
        if db_manager:
            query = "SELECT id, title, price FROM service ORDER BY title"
            services = db_manager.execute_query(query, fetch=True)

            for service in services:
                combobox.addItem(f"{service['title']} ({service['price']} руб.)", service['id'])
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            cursor.execute("SELECT id, title, price FROM service ORDER BY title")
            services = cursor.fetchall()

            for service in services:
                combobox.addItem(f"{service[1]} ({service[2]} руб.)", service[0])

            cursor.close()
            conn.close()
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось загрузить список услуг: {str(e)}")
        return False
    return True


def update_guest_combobox(combobox, db_config=None, db_manager=None):
    """Обновляет список постояльцев в комбобоксе"""
    combobox.clear()

    try:
        if db_manager:
            query = """
                    SELECT id, name, surname, patronymic, passport 
                    FROM guest 
                    ORDER BY surname, name
                    """
            guests = db_manager.execute_query(query, fetch=True)

            for guest in guests:
                patronymic_str = f" {guest['patronymic']}" if guest['patronymic'] else ""
                display_text = f"{guest['surname']} {guest['name']}{patronymic_str} (паспорт: {guest['passport']})"
                combobox.addItem(display_text, guest['id'])
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            cursor.execute("SELECT id, name, surname, patronymic, passport FROM guest ORDER BY surname, name")
            guests = cursor.fetchall()

            for guest in guests:
                patronymic_str = f" {guest[3]}" if guest[3] else ""
                display_text = f"{guest[2]} {guest[1]}{patronymic_str} (паспорт: {guest[4]})"
                combobox.addItem(display_text, guest[0])

            cursor.close()
            conn.close()
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось загрузить список постояльцев: {str(e)}")
        return False
    return True


def update_guest_services_table(table, label, guest_id, guest_name, db_config=None, db_manager=None):
    """Обновляет таблицу услуг выбранного постояльца"""
    table.setRowCount(0)

    if guest_id is None:
        return False

    # Обновляем заголовок таблицы
    if label:
        label.setText(f"Услуги постояльца: {guest_name}")

    try:
        # Запрос услуг постояльца
        query = """
        SELECT sfg.id, s.title, s.price, sfg.date 
        FROM service_for_guest sfg
        JOIN service s ON sfg.id_service = s.id
        WHERE sfg.id_guest = %s
        ORDER BY sfg.date DESC
        """

        if db_manager:
            services = db_manager.execute_query(query, params=(guest_id,), fetch=True)
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(query, (guest_id,))
            services = cursor.fetchall()
            cursor.close()
            conn.close()

        # Заполняем таблицу
        for row, service in enumerate(services):
            table.insertRow(row)

            if isinstance(service, dict):
                # Если используем db_manager
                table.setItem(row, 0, QTableWidgetItem(service['title']))
                table.setItem(row, 1, QTableWidgetItem(f"{service['price']} руб."))
                date_time = service['date'].strftime("%d.%m.%Y %H:%M") if service['date'] else "-"
                table.setItem(row, 2, QTableWidgetItem(date_time))
                table.setItem(row, 3, QTableWidgetItem(str(service['id'])))
            else:
                # Если используем прямое подключение
                table.setItem(row, 0, QTableWidgetItem(service[1]))
                table.setItem(row, 1, QTableWidgetItem(f"{service[2]} руб."))
                date_time = service[3].strftime("%d.%m.%Y %H:%M") if service[3] else "-"
                table.setItem(row, 2, QTableWidgetItem(date_time))
                table.setItem(row, 3, QTableWidgetItem(str(service[0])))

        # Подгоняем ширину столбцов под содержимое
        table.resizeColumnsToContents()

    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось загрузить услуги постояльца: {str(e)}")
        return False
    return True


def add_service_for_guest(guest_id, service_id, service_date, db_config=None, db_manager=None):
    """Добавляет выбранную услугу выбранному постояльцу"""
    if guest_id is None:
        QMessageBox.warning(None, "Предупреждение", "Выберите постояльца")
        return False

    if service_id is None:
        QMessageBox.warning(None, "Предупреждение", "Выберите услугу")
        return False

    try:
        # Добавляем услугу для постояльца
        query = """
        INSERT INTO service_for_guest (id_guest, id_service, date)
        VALUES (%s, %s, %s)
        """

        if db_manager:
            db_manager.execute_query(query, params=(guest_id, service_id, service_date))
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(query, (guest_id, service_id, service_date))
            conn.commit()
            cursor.close()
            conn.close()

        QMessageBox.information(None, "Успех", "Услуга успешно добавлена")
        return True
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось добавить услугу: {str(e)}")
        return False


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
            # Проверяем, используется ли db_manager или прямое подключение
            if hasattr(self, 'db_manager'):
                query = "UPDATE service SET title = %s, price = %s WHERE id = %s"
                self.db_manager.execute_query(query, params=(title, price, self.service_edit_id))
            else:
                conn = psycopg2.connect(**self.db_config)
                cursor = conn.cursor()
                cursor.execute("UPDATE service SET title = %s, price = %s WHERE id = %s",
                               (title, price, self.service_edit_id))
                conn.commit()
                cursor.close()
                conn.close()

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

def delete_service_for_guest(service_id, service_name, db_config=None, db_manager=None):
    """Удаляет выбранную услугу постояльца"""
    if not service_id:
        QMessageBox.warning(None, "Предупреждение", "Выберите услугу для удаления")
        return False

    # Подтверждение удаления
    reply = QMessageBox.question(None, "Подтверждение",
                                 f"Вы уверены, что хотите удалить услугу '{service_name}'?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

    if reply == QMessageBox.No:
        return False

    try:
        # Удаляем услугу
        query = "DELETE FROM service_for_guest WHERE id = %s"

        if db_manager:
            db_manager.execute_query(query, params=(service_id,))
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(query, (service_id,))
            conn.commit()
            cursor.close()
            conn.close()

        QMessageBox.information(None, "Успех", "Услуга успешно удалена")
        return True
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось удалить услугу: {str(e)}")
        return False

def update_services_table(table, db_config=None, db_manager=None):
    """Обновляет таблицу доступных услуг"""
    table.setRowCount(0)

    try:
        if db_manager:
            query = "SELECT id, title, price FROM service ORDER BY title"
            services = db_manager.execute_query(query, fetch=True)
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, price FROM service ORDER BY title")
            services = cursor.fetchall()
            cursor.close()
            conn.close()

        # Заполняем таблицу
        for row, service in enumerate(services):
            table.insertRow(row)

            # Получаем данные в зависимости от типа результата
            if isinstance(service, dict):
                service_id = service['id']
                title = service['title']
                price = service['price']
            else:
                service_id = service[0]
                title = service[1]
                price = service[2]

            table.setItem(row, 0, QTableWidgetItem(title))
            table.setItem(row, 1, QTableWidgetItem(f"{price:.2f}"))
            table.setItem(row, 2, QTableWidgetItem(str(service_id)))

        # Подгоняем ширину столбцов под содержимое
        table.resizeColumnsToContents()
        return True
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось загрузить список услуг: {str(e)}")
        return False

def add_service_to_list(title, price, db_config=None, db_manager=None):
    """Добавляет новую услугу в список"""
    if not title.strip():
        QMessageBox.warning(None, "Предупреждение", "Введите название услуги")
        return False

    try:
        if db_manager:
            query = "INSERT INTO service (title, price) VALUES (%s, %s)"
            db_manager.execute_query(query, params=(title, price))
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO service (title, price) VALUES (%s, %s)", (title, price))
            conn.commit()
            cursor.close()
            conn.close()

        QMessageBox.information(None, "Успех", "Услуга успешно добавлена")
        return True
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось добавить услугу: {str(e)}")
        return False

def update_service(service_id, title, price, db_config=None, db_manager=None):
    """Обновляет существующую услугу"""
    if not title.strip():
        QMessageBox.warning(None, "Предупреждение", "Введите название услуги")
        return False

    try:
        if db_manager:
            query = "UPDATE service SET title = %s, price = %s WHERE id = %s"
            db_manager.execute_query(query, params=(title, price, service_id))
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("UPDATE service SET title = %s, price = %s WHERE id = %s",
                           (title, price, service_id))
            conn.commit()
            cursor.close()
            conn.close()

        QMessageBox.information(None, "Успех", "Услуга успешно обновлена")
        return True
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось обновить услугу: {str(e)}")
        return False

def delete_service_from_list(service_id, title, db_config=None, db_manager=None):
    """Удаляет услугу из списка"""
    if not service_id:
        QMessageBox.warning(None, "Предупреждение", "Выберите услугу для удаления")
        return False

    # Подтверждение удаления
    reply = QMessageBox.question(None, "Подтверждение",
                                 f"Вы уверены, что хотите удалить услугу '{title}'?\n"
                                 f"Это также удалит все связанные записи об оказании этой услуги постояльцам.",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

    if reply == QMessageBox.No:
        return False

    try:
        if db_manager:
            query = "DELETE FROM service WHERE id = %s"
            db_manager.execute_query(query, params=(service_id,))
        else:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM service WHERE id = %s", (service_id,))
            conn.commit()
            cursor.close()
            conn.close()

        QMessageBox.information(None, "Успех", "Услуга успешно удалена")
        return True
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Не удалось удалить услугу: {str(e)}")
        return False
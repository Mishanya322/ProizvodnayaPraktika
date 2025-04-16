import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                              QTableWidgetItem, QVBoxLayout, QWidget,
                              QPushButton, QDialog, QLabel, QFormLayout,
                              QListWidget, QListWidgetItem, QComboBox, 
                              QHBoxLayout, QTabWidget, QFileDialog,
                              QLineEdit, QMessageBox, QHeaderView, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

Base = declarative_base()

font_path = os.path.join(os.getcwd(), 'DejaVuSans.ttf')
if os.path.exists(font_path):
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
        print(f"Шрифт DejaVuSans зарегистрирован успешно из {font_path}")
    except Exception as e:
        print(f"Ошибка регистрации шрифта: {e}")
else:
    print(f"Файл шрифта {font_path} не найден. Используется fallback (Helvetica).")
    pdfmetrics.registerFont(TTFont('Helvetica', 'Helvetica'))

class Corpus(Base):
    __tablename__ = 'corpus'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

class Otdelenie(Base):
    __tablename__ = 'otdelenie'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    corpus = Column(Integer, ForeignKey('corpus.id'))

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    position = Column(String(100))
    otdelenie = Column(Integer, ForeignKey('otdelenie.id'))

class Schedule(Base):
    __tablename__ = 'schedule'
    id = Column(Integer, primary_key=True)
    employee = Column(Integer, ForeignKey('employees.id'))
    shift_date = Column(Date)

class Database:
    def __init__(self):
        self.engine = create_engine("postgresql://postgres:1234@localhost:5432/hospital_db")
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        Base.metadata.create_all(self.engine)

    def close(self):
        self.session.close()

class EmployeeRepository:
    def __init__(self, db):
        self.db = db

    def get_employee_details(self, emp_id):
        result = self.db.session.query(Employee, Otdelenie).join(Otdelenie).filter(Employee.id == emp_id).first()
        if result:
            employee, otdelenie = result
            shift_count = self.db.session.query(Schedule).filter(Schedule.employee == emp_id).count()
            return {
                'name': employee.name, 
                'position': employee.position, 
                'otdelenie': otdelenie.name, 
                'shifts': shift_count
            }
        return None

    def get_all_employees(self):
        employees = self.db.session.query(Employee, Otdelenie).join(Otdelenie).order_by(Employee.name).all()
        result = []
        for emp, otd in employees:
            shift_count = self.db.session.query(Schedule).filter(Schedule.employee == emp.id).count()
            result.append((emp.id, emp.name, emp.position, otd.name, shift_count))
        return result

    def get_available_employees(self, shift_date):
        scheduled_ids = self.db.session.query(Schedule.employee).filter(Schedule.shift_date == shift_date).all()
        scheduled_ids = [id_tuple[0] for id_tuple in scheduled_ids]
        employees = self.db.session.query(Employee, Otdelenie).join(Otdelenie).filter(Employee.id.notin_(scheduled_ids)).order_by(Employee.name).all()
        return [(emp.id, emp.name) for emp, otd in employees]

    def add_employee(self, name, position, otdelenie_name):
        otdelenie = self.db.session.query(Otdelenie).filter(Otdelenie.name == otdelenie_name).first()
        if not otdelenie:
            QMessageBox.warning(None, "Ошибка", f"Отделение {otdelenie_name} не найдено")
            return False
        
        new_employee = Employee(name=name, position=position, otdelenie=otdelenie.id)
        self.db.session.add(new_employee)
        self.db.session.commit()
        return True

    def get_all_otdeleniya(self):
        return self.db.session.query(Otdelenie).order_by(Otdelenie.name).all()

class ScheduleRepository:
    def __init__(self, db):
        self.db = db

    def get_shifts_by_date(self, shift_date):
        shifts = self.db.session.query(Schedule, Employee).join(Employee).filter(Schedule.shift_date == shift_date).all()
        return [(shift.id, shift.employee, employee.name) for shift, employee in shifts]

    def add_shift(self, employee_id, shift_date):
        new_shift = Schedule(employee=employee_id, shift_date=shift_date)
        self.db.session.add(new_shift)
        self.db.session.commit()

    def remove_shift(self, shift_id):
        shift = self.db.session.query(Schedule).filter(Schedule.id == shift_id).first()
        if shift:
            self.db.session.delete(shift)
            self.db.session.commit()
            return True
        return False

    def get_month_schedule(self, start_date):
        end_date = start_date.replace(day=1) + timedelta(days=31)
        if end_date.month > start_date.month:
            end_date = end_date.replace(day=1) - timedelta(days=1)
        shifts = self.db.session.query(Schedule, Employee).join(Employee).filter(
            Schedule.shift_date >= start_date.date(),
            Schedule.shift_date <= end_date.date()
        ).all()
        schedule_dict = {}
        for shift, employee in shifts:
            date_str = shift.shift_date.strftime('%d.%m.%Y')
            if date_str not in schedule_dict:
                schedule_dict[date_str] = []
            schedule_dict[date_str].append(employee.name)
        return schedule_dict

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вход в систему")
        self.setFixedSize(300, 200)
        self.setStyleSheet("background-color: #F7F9FC; border-radius: 10px;")
        
        layout = QFormLayout()
        
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Введите логин (ФИО)")
        self.login_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                font: 14px Arial;
            }
        """)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Введите пароль")
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                font: 14px Arial;
            }
        """)
        
        login_btn = QPushButton("Войти")
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #5E81AC;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #81A1C1;
            }
        """)
        login_btn.clicked.connect(self.check_credentials)
        
        layout.addRow("Логин (ФИО):", self.login_input)
        layout.addRow("Пароль (Отделение):", self.password_input)
        layout.addWidget(login_btn)
        layout.setSpacing(15)
        self.setLayout(layout)
        
        self.is_admin = False
        self.employee_id = None
        
    def check_credentials(self):
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()
        
        if login == "admin" and password == "admin":
            self.is_admin = True
            self.accept()
            return
            
        db = Database()
        employee = db.session.query(Employee, Otdelenie).join(Otdelenie).filter(Employee.name == login).first()
        if employee:
            employee, otdelenie = employee
            if otdelenie.name == password:
                self.is_admin = False
                self.employee_id = employee.id
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Неверный пароль")
                self.password_input.clear()
        else:
            QMessageBox.warning(self, "Ошибка", "Сотрудник не найден")
            self.login_input.clear()
            self.password_input.clear()
        db.close()

class EmployeeCardDialog(QDialog):
    def __init__(self, employee_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Карточка сотрудника")
        self.setStyleSheet("background-color: #F7F9FC; border-radius: 10px;")
        layout = QFormLayout()
        
        label_font = QFont("Arial", 12)
        value_font = QFont("Arial", 14, QFont.Bold)
        
        name_label = QLabel("ФИО:")
        name_label.setFont(label_font)
        name_value = QLabel(employee_data['name'])
        name_value.setFont(value_font)
        
        pos_label = QLabel("Должность:")
        pos_label.setFont(label_font)
        pos_value = QLabel(employee_data['position'])
        pos_value.setFont(value_font)
        
        otd_label = QLabel("Отделение:")
        otd_label.setFont(label_font)
        otd_value = QLabel(employee_data['otdelenie'])
        otd_value.setFont(value_font)
        
        shifts_label = QLabel("Количество смен:")
        shifts_label.setFont(label_font)
        shifts_value = QLabel(str(employee_data['shifts']))
        shifts_value.setFont(value_font)
        
        layout.addRow(name_label, name_value)
        layout.addRow(pos_label, pos_value)
        layout.addRow(otd_label, otd_value)
        layout.addRow(shifts_label, shifts_value)
        
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #5E81AC;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #81A1C1;
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class AddEmployeeDialog(QDialog):
    def __init__(self, employee_repo, parent=None):
        super().__init__(parent)
        self.employee_repo = employee_repo
        self.setWindowTitle("Добавить сотрудника")
        self.setFixedSize(400, 300)
        self.setStyleSheet("background-color: #F7F9FC; border-radius: 10px;")

        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите ФИО")
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                font: 14px Arial;
            }
        """)

        self.position_input = QLineEdit()
        self.position_input.setPlaceholderText("Введите должность")
        self.position_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                font: 14px Arial;
            }
        """)

        self.otdelenie_combo = QComboBox()
        otdeleniya = self.employee_repo.get_all_otdeleniya()
        self.otdelenie_combo.addItems([otd.name for otd in otdeleniya])
        self.otdelenie_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                font: 14px Arial;
            }
        """)

        add_btn = QPushButton("Добавить")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #88C0D0;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #A3BE8C;
            }
        """)
        add_btn.clicked.connect(self.add_employee)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #BF616A;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #D08770;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        layout.addRow("ФИО:", self.name_input)
        layout.addRow("Должность:", self.position_input)
        layout.addRow("Отделение:", self.otdelenie_combo)
        layout.addRow(add_btn, cancel_btn)
        layout.setSpacing(15)
        self.setLayout(layout)

    def add_employee(self):
        name = self.name_input.text().strip()
        position = self.position_input.text().strip()
        otdelenie_name = self.otdelenie_combo.currentText()

        if not name or not position or not otdelenie_name:
            QMessageBox.warning(self, "Ошибка", "Все поля должны быть заполнены")
            return

        if self.employee_repo.add_employee(name, position, otdelenie_name):
            QMessageBox.information(self, "Успех", "Сотрудник успешно добавлен")
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось добавить сотрудника")

class ShiftDialog(QDialog):
    def __init__(self, shift_date, employees, parent_window=None):
        super().__init__(parent_window)
        self.setWindowTitle(f"Дежурные {shift_date.strftime('%d.%m.%Y')}")
        self.setStyleSheet("background-color: #F7F9FC; border-radius: 10px;")
        self.setFixedSize(500, 400)
        self.shift_date = shift_date
        self.employees = employees
        self.employee_repo = parent_window.employee_repo if parent_window else None
        self.schedule_repo = parent_window.schedule_repo if parent_window else None
        self.parent_window = parent_window
        
        layout = QVBoxLayout()
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #5E81AC;
                color: white;
            }
        """)
        self.update_employee_list()
        
        self.list_widget.itemClicked.connect(self.show_employee_card)
        
        self.add_layout = QHBoxLayout()
        self.employee_combo = QComboBox()
        self.employee_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                font: 14px Arial;
            }
        """)
        self.load_available_employees()
        
        self.add_btn = QPushButton("Добавить дежурного")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #88C0D0;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #A3BE8C;
            }
        """)
        self.add_btn.clicked.connect(self.add_employee_to_shift)
        
        self.add_layout.addWidget(self.employee_combo)
        self.add_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("Удалить дежурного")
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #BF616A;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #D08770;
            }
        """)
        self.remove_btn.clicked.connect(self.remove_employee_from_shift)
        
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #5E81AC;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #81A1C1;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        layout.addWidget(self.list_widget)
        
        if self.parent_window and self.parent_window.is_admin:
            layout.addLayout(self.add_layout)
            layout.addWidget(self.remove_btn)
        else:
            self.employee_combo.setEnabled(False)
            self.add_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            self.employee_combo.setVisible(False)
            self.add_btn.setVisible(False)
            self.remove_btn.setVisible(False)
        
        layout.addWidget(close_btn)
        layout.setSpacing(15)
        self.setLayout(layout)
        
    def update_employee_list(self):
        self.list_widget.clear()
        if not self.employees:
            item = QListWidgetItem("В этот день дежурных нет")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setFont(QFont("Arial", 14, QFont.Bold))
            item.setForeground(QColor("#5E81AC"))
            self.list_widget.addItem(item)
        else:
            for shift_id, emp_id, emp_name in self.employees:
                item = QListWidgetItem(emp_name)
                item.setData(Qt.UserRole, (shift_id, emp_id))
                item.setFont(QFont("Arial", 14))
                self.list_widget.addItem(item)
        
    def load_available_employees(self):
        if self.employee_repo:
            employees = self.employee_repo.get_available_employees(self.shift_date.date())
            if employees:
                self.employee_combo.clear()
                for emp_id, emp_name in employees:
                    self.employee_combo.addItem(emp_name, emp_id)
        
    def add_employee_to_shift(self):
        if not self.employee_combo or not self.schedule_repo:
            return
        
        emp_id = self.employee_combo.currentData()
        if not emp_id:
            return
        
        self.schedule_repo.add_shift(emp_id, self.shift_date.date())
        self.employees = self.schedule_repo.get_shifts_by_date(self.shift_date.date())
        
        self.update_employee_list()
        self.load_available_employees()
        if self.parent_window:
            self.parent_window.load_schedule()
        
    def remove_employee_from_shift(self):
        if not self.parent_window:
            QMessageBox.warning(self, "Ошибка", "Нет доступа к родительскому окну")
            return
        
        selected_items = self.list_widget.selectedItems()
        if not selected_items or not self.parent_window.is_admin:
            QMessageBox.warning(self, "Ошибка", "Выберите сотрудника для удаления или нет прав администратора")
            return
        
        shift_id, _ = selected_items[0].data(Qt.UserRole)
        if self.schedule_repo and self.schedule_repo.remove_shift(shift_id):
            self.employees = self.schedule_repo.get_shifts_by_date(self.shift_date.date())
            self.update_employee_list()
            self.load_available_employees()
            if self.parent_window:
                self.parent_window.load_schedule()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить дежурство")

    def show_employee_card(self, item):
        if not self.employee_repo:
            return
        _, emp_id = item.data(Qt.UserRole)
        data = self.employee_repo.get_employee_details(emp_id)
        if data:
            dialog = EmployeeCardDialog(data, self)
            dialog.exec()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = None
        self.employee_repo = None
        self.schedule_repo = None
        self.is_admin = False
        self.employee_id = None
        self.current_date = datetime.now()
        
        self.setWindowTitle("График дежурств больницы")
        self.init_db_and_repos()
        self.init_ui()
        self.login()

    def init_db_and_repos(self):
        self.db = Database()
        self.employee_repo = EmployeeRepository(self.db)
        self.schedule_repo = ScheduleRepository(self.db)

    def login(self):
        login_dialog = LoginDialog(self)
        if login_dialog.exec() != QDialog.Accepted:
            sys.exit(0)
            
        self.is_admin = login_dialog.is_admin
        self.employee_id = login_dialog.employee_id
        self.update_ui_access()
        self.showMaximized()
        self.show()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        central_widget.setStyleSheet("background-color: #ECEFF4;")
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #D8DEE9;
                background-color: #ECEFF4;
                border-radius: 10px;
            }
            QTabBar::tab {
                background-color: #81A1C1;
                color: white;
                padding: 12px 20px;
                margin-right: 5px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font: bold 14px Arial;
            }
            QTabBar::tab:selected {
                background-color: #5E81AC;
            }
        """)
        
        self.schedule_widget = QWidget()
        schedule_layout = QVBoxLayout(self.schedule_widget)
        
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Предыдущий месяц")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #88C0D0;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #A3BE8C;
            }
        """)
        self.prev_btn.clicked.connect(self.prev_month)
        
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.month_label.setStyleSheet("color: #2E3440;")
        
        self.next_btn = QPushButton("Следующий месяц")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #88C0D0;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #A3BE8C;
            }
        """)
        self.next_btn.clicked.connect(self.next_month)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.month_label)
        nav_layout.addWidget(self.next_btn)
        
        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                gridline-color: #D8DEE9;
            }
            QHeaderView::section {
                background-color: #5E81AC;
                color: white;
                padding: 10px;
                border: 1px solid #D8DEE9;
                font: bold 14px Arial;
            }
        """)
        self.table.cellClicked.connect(self.show_shift_details)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        button_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Обновить график")
        self.refresh_btn.setObjectName("refresh_schedule_btn")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #88C0D0;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #A3BE8C;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_schedule)
        
        self.pdf_btn = QPushButton("Сохранить в PDF")
        self.pdf_btn.setObjectName("save_pdf_btn")
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #D08770;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #EBCB8B;
            }
        """)
        self.pdf_btn.clicked.connect(self.generate_pdf)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.pdf_btn)
        
        schedule_layout.addLayout(nav_layout)
        schedule_layout.addWidget(self.table)
        schedule_layout.addLayout(button_layout)
        schedule_layout.setSpacing(20)
        
        self.employees_widget = QWidget()
        employees_layout = QVBoxLayout(self.employees_widget)
        
        self.employees_list = QListWidget()
        self.employees_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #D8DEE9;
                border-radius: 8px;
                background-color: white;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #5E81AC;
                color: white;
            }
        """)
        self.employees_list.itemClicked.connect(self.show_employee_card_from_list)
        
        self.refresh_employees_btn = QPushButton("Обновить список")
        self.refresh_employees_btn.setObjectName("refresh_employees_btn")
        self.refresh_employees_btn.setStyleSheet("""
            QPushButton {
                background-color: #88C0D0;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #A3BE8C;
            }
        """)
        self.refresh_employees_btn.clicked.connect(self.load_employees)
        
        self.add_employee_btn = QPushButton("Добавить сотрудника")
        self.add_employee_btn.setObjectName("add_employee_btn")
        self.add_employee_btn.setStyleSheet("""
            QPushButton {
                background-color: #88C0D0;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #A3BE8C;
            }
        """)
        self.add_employee_btn.clicked.connect(self.show_add_employee_dialog)

        employees_layout.addWidget(self.employees_list)
        employees_layout.addWidget(self.refresh_employees_btn)
        employees_layout.addWidget(self.add_employee_btn)
        employees_layout.setSpacing(20)
        
        self.tab_widget.addTab(self.schedule_widget, "График дежурств")
        self.tab_widget.addTab(self.employees_widget, "Сотрудники")

        self.logout_btn = QPushButton("Выйти из учетной записи")
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #BF616A;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #D08770;
            }
        """)
        self.logout_btn.clicked.connect(self.logout)

        main_layout.addWidget(self.tab_widget)
        main_layout.addWidget(self.logout_btn, alignment=Qt.AlignRight)
        main_layout.setContentsMargins(10, 10, 10, 10)

    def update_ui_access(self):
        refresh_btn = self.schedule_widget.findChild(QPushButton, "refresh_schedule_btn")
        if refresh_btn:
            refresh_btn.setVisible(self.is_admin)
        else:
            print("Кнопка 'Обновить график' не найдена")

        pdf_btn = self.schedule_widget.findChild(QPushButton, "save_pdf_btn")
        if pdf_btn:
            pdf_btn.setVisible(self.is_admin)
        else:
            print("Кнопка 'Сохранить в PDF' не найдена")

        self.tab_widget.setTabEnabled(1, self.is_admin)
        self.tab_widget.setTabVisible(1, self.is_admin)

        add_employee_btn = self.employees_widget.findChild(QPushButton, "add_employee_btn")
        if add_employee_btn:
            add_employee_btn.setEnabled(self.is_admin)
        else:
            print("Кнопка 'Добавить сотрудника' не найдена")

        self.load_schedule()
        self.load_employees()

    def logout(self):
        self.hide()
        if self.db:
            self.db.close()

        self.is_admin = False
        self.employee_id = None

        self.init_db_and_repos()
        self.login()

    def load_schedule(self):
        start_of_month = self.current_date.replace(day=1)
        if start_of_month.month < 12:
            next_month = start_of_month.replace(month=start_of_month.month + 1, year=start_of_month.year)
        else:
            next_month = start_of_month.replace(month=1, year=start_of_month.year + 1)
        days_in_month = (next_month - start_of_month).days
        
        months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        self.month_label.setText(f"{months[start_of_month.month - 1]} {start_of_month.year}")
        
        first_day_weekday = start_of_month.weekday()
        total_slots = days_in_month + first_day_weekday
        weeks = (total_slots + 6) // 7
        self.table.setRowCount(weeks)
        self.table.setColumnCount(7)
        
        headers = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        self.table.setHorizontalHeaderLabels(headers)
        
        today = datetime.now()
        self.table.clearContents()
        
        for day in range(days_in_month):
            current_date = start_of_month + timedelta(days=day)
            total_position = day + first_day_weekday
            row = total_position // 7
            col = total_position % 7
            
            employees = self.schedule_repo.get_shifts_by_date(current_date.date())
            item = QTableWidgetItem()
            employee_count = len(employees) if employees else 0
            item.setText(f"{day + 1}\n{employee_count} чел.")
            item.setData(Qt.UserRole, {
                'date': current_date,
                'employees': employees if employees else []
            })
            item.setTextAlignment(Qt.AlignCenter)
            item.setFont(QFont("Arial", 12))
            
            if current_date.date() == today.date():
                item.setBackground(QColor("#E5E9F0"))
            elif employee_count > 0:
                item.setBackground(QColor("#EBE9D8"))
            else:
                item.setBackground(QColor("#FFFFFF"))
                
            self.table.setItem(row, col, item)
        
        for col in range(7):
            self.table.setColumnWidth(col, self.table.width() // 7)
        for row in range(weeks):
            self.table.setRowHeight(row, 80)

    def generate_pdf(self):
        start_of_month = self.current_date.replace(day=1)
        months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        
        month_index = start_of_month.month - 1
        if not (0 <= month_index < len(months)):
            month_name = "Неизвестный месяц"
        else:
            month_name = months[month_index]
        
        print(f"month_name перед Paragraph: {month_name}")
        title_text = f"График дежурств: {month_name} {start_of_month.year}"
        print(f"title_text: {title_text}")
        
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить PDF", 
                                                 f"График_дежурств_{month_name}_{start_of_month.year}.pdf", 
                                                 "PDF Files (*.pdf)")
        if not filename:
            return
        
        schedule_data = self.schedule_repo.get_month_schedule(start_of_month)
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        
        styles = getSampleStyleSheet()
        
        font_name = 'DejaVuSans' if pdfmetrics.getFont('DejaVuSans') else 'Helvetica'
        print(f"Используемый шрифт: {font_name}")
 
        logo_style = ParagraphStyle(
            name='LogoStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=14,
            textColor=colors.black,
            alignment=1
        )
        
        title_style = ParagraphStyle(
            name='TitleStyle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=24,
            textColor=colors.blue,
            spaceAfter=12,
            alignment=1
        )
        
        info_style = ParagraphStyle(
            name='InfoStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            leading=14,
            alignment=1
        )
        
        schedule_style = ParagraphStyle(
            name='ScheduleStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            leading=16,
            leftIndent=20,
            spaceAfter=6
        )
        
        footer_style = ParagraphStyle(
            name='FooterStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=12,
            alignment=1
        )
        
        logo_path = os.path.join(os.getcwd(), 'logo.jpg')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=250, height=250)
            elements.append(logo)
        else:
            logo_text = Paragraph("Логотип больницы", logo_style)
            elements.append(logo_text)
        
        title = Paragraph(title_text, title_style)
        elements.append(title)
        
        hospital_info = Paragraph(
            "Республиканская клиническая больница имени Г.Я. Ремишевской<br/>Адрес: пр. Ленина д. 23<br/>Телефон: +7 390 224-82-54",
            info_style
        )
        elements.append(hospital_info)
        
        elements.append(Paragraph("<br/>", styles['Normal']))
        
        schedule_text = "Список дежурств:<br/>\n"
        for i, (date, employees) in enumerate(sorted(schedule_data.items()), 1):
            schedule_text += f"<b>{i}.</b> Дежурства на {date}:<br/>\n"
            if employees:
                schedule_text += "   - <i>Дежурные:</i><br/>\n"
                for j, employee in enumerate(employees, 1):
                    schedule_text += f"      <b>{j}.</b> {employee}<br/>\n"
            else:
                schedule_text += "   - <i>Дежурных нет</i><br/>\n"
            schedule_text += "<br/>\n"
        
        schedule_paragraph = Paragraph(schedule_text, schedule_style)
        elements.append(schedule_paragraph)
        
        footer_text = (
            f"Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}<br/>"
            "Отдел кадров: 8 (3902) 248-263<br/>"
            "Электронная почта: kadry@gospital.ru"
        )
        footer = Paragraph(footer_text, footer_style)
        elements.append(footer)
        
        doc.build(elements)
        print(f"PDF сохранен как {filename}")

    def load_employees(self):
        self.employees_list.clear()
        employees = self.employee_repo.get_all_employees()
        if employees:
            for emp_id, name, position, otdelenie, shifts in employees:
                item = QListWidgetItem(f"{name} - {position} ({otdelenie}, {shifts} смен)")
                item.setData(Qt.UserRole, emp_id)
                item.setFont(QFont("Arial", 14))
                self.employees_list.addItem(item)
    
    def show_employee_card_from_list(self, item):
        emp_id = item.data(Qt.UserRole)
        data = self.employee_repo.get_employee_details(emp_id)
        if data:
            dialog = EmployeeCardDialog(data, self)
            dialog.exec()

    def show_add_employee_dialog(self):
        dialog = AddEmployeeDialog(self.employee_repo, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_employees()
            
    def prev_month(self):
        self.current_date = self.current_date.replace(day=1) - timedelta(days=1)
        self.load_schedule()
        
    def next_month(self):
        self.current_date = self.current_date.replace(day=1)
        if self.current_date.month < 12:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        else:
            self.current_date = self.current_date.replace(month=1, year=self.current_date.year + 1)
        self.load_schedule()
        
    def show_shift_details(self, row, col):
        item = self.table.item(row, col)
        if item:
            data = item.data(Qt.UserRole)
            dialog = ShiftDialog(data['date'], data['employees'], self)
            dialog.exec()
            
    def closeEvent(self, event):
        if self.db:
            self.db.close()
        event.accept()

app = QApplication()
window = MainWindow()
window.show()
app.exec()
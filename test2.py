import unittest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QMessageBox
from datetime import datetime
app = QApplication()
class Employee:
    def __init__(self, id, name):
        self.id, self.name = id, name
class MainWindow:
    def __init__(self):
        self.is_admin = True
        self.schedule_repo = Mock()
        self.load_schedule = Mock()
class ShiftTester:
    def __init__(self, shift_date, employees, parent_window=None):
        self.shift_date = shift_date
        self.employees = employees
        self.parent_window = parent_window
        self.list_widget = Mock()
    def update_employee_list(self):
        self.list_widget.clear()
    def remove_employee_from_shift(self, selected_shift_id, selected_emp_id):
        if not self.parent_window or not self.parent_window.is_admin:
            return False
        selected_items = [Mock()]
        selected_items[0].data.return_value = (selected_shift_id, selected_emp_id)
        self.list_widget.selectedItems.return_value = selected_items
        shift_id, _ = selected_items[0].data()
        if self.parent_window.schedule_repo.remove_shift(shift_id):
            self.employees = self.parent_window.schedule_repo.get_shifts_by_date(self.shift_date)
            self.update_employee_list()
            self.parent_window.load_schedule()
            return True
        return False
class TestShiftLogic(unittest.TestCase):
    def setUp(self):
        self.shift_date = datetime.strptime("20.03.2025", "%d.%m.%Y")
        self.employee_id, self.shift_id = 1, 100
        self.employees = [(self.shift_id, self.employee_id, "Иванов Иван Иванович")]
        self.parent_window = MainWindow()
        self.tester = ShiftTester(self.shift_date, self.employees, self.parent_window)
    def test_remove_employee_from_shift(self):
        self.parent_window.schedule_repo.remove_shift.return_value = True
        self.parent_window.schedule_repo.get_shifts_by_date.return_value = []
        self.assertTrue(self.tester.remove_employee_from_shift(self.shift_id, self.employee_id))
        self.assertEqual(self.tester.employees, [])
        self.tester.list_widget.clear.assert_called_once()
        self.tester.parent_window.load_schedule.assert_called_once()
result = unittest.TextTestRunner().run(unittest.TestSuite([TestShiftLogic('test_remove_employee_from_shift')]))
msg = f"Тесты {'успешны' if result.wasSuccessful() else 'провалены'}! Пройдено: {result.testsRun}"
msg_box = QMessageBox()
msg_box.setWindowTitle("Результаты")
msg_box.setText(msg)
msg_box.exec()
app.exec()
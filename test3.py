import unittest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication()
class Employee:
    def __init__(self, id, name, position):
        self.id, self.name, self.position = id, name, position
class EmployeeCardTester:
    def __init__(self):
        self.dialog = Mock()
    def show_employee_card(self, employee_id):
        employee = Employee(id=employee_id, name="Иванов Иван Иванович", position="Хирург")
        employee_data = {
            "name": employee.name,
            "position": employee.position,
            "otdelenie": "Хирургия",
            "shifts_count": 5
        }
        self.dialog.name_label.setText(employee_data["name"])
        self.dialog.position_label.setText(employee_data["position"])
        self.dialog.otdelenie_label.setText(employee_data["otdelenie"])
        self.dialog.shifts_label.setText(str(employee_data["shifts_count"]))
        return employee_data
class TestEmployeeCard(unittest.TestCase):
    def setUp(self):
        self.tester = EmployeeCardTester()
    def test_show_employee_card(self):
        result = self.tester.show_employee_card(1)
        expected = {"name": "Иванов Иван Иванович", "position": "Хирург", "otdelenie": "Хирургия", "shifts_count": 5}
        self.assertEqual(result, expected)
result = unittest.TextTestRunner().run(unittest.TestSuite([TestEmployeeCard('test_show_employee_card')]))
msg = f"Тесты {'успешны' if result.wasSuccessful() else 'провалены'}! Пройдено: {result.testsRun}"
msg_box = QMessageBox()
msg_box.setWindowTitle("Результаты")    
msg_box.setText(msg)
msg_box.exec()
app.exec()
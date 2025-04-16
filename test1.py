import unittest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication()
class Employee:
    def __init__(self, id, name):
        self.id, self.name = id, name
class Otdelenie:
    def __init__(self, name):
        self.name = name
class LoginTester:
    def __init__(self):
        self.is_admin = False
        self.employee_id = None
        self.accept = Mock()
        self.password_input = Mock()
    def check_credentials(self, login, password, mock_db, mock_msgbox):
        if login == "admin" and password == "admin":
            self.is_admin = True
            self.accept()
            return
        mock_employee = Employee(id=1, name="Иванов Иван Иванович")
        mock_otdelenie = Otdelenie(name="Хирургия")
        mock_db.return_value.session.query.return_value.filter.return_value.first.return_value = (
            mock_employee, mock_otdelenie) if login == "Иванов Иван Иванович" else None
        if login == "Иванов Иван Иванович" and mock_otdelenie.name == password:
            self.employee_id = mock_employee.id
            self.accept()
        else:
            mock_msgbox.warning(None, "Ошибка", "Неверный пароль")
            self.password_input.clear()
class TestLoginLogic(unittest.TestCase):
    def setUp(self):
        self.tester = LoginTester()
    @patch('__main__.QMessageBox')
    @patch('__main__.Mock')
    def test_wrong_password(self, mock_db, mock_msgbox):
        self.tester.check_credentials("Иванов Иван Иванович", "Терапия", mock_db, mock_msgbox)
        mock_msgbox.warning.assert_called_once_with(None, "Ошибка", "Неверный пароль")
        self.tester.password_input.clear.assert_called_once()
        self.tester.accept.assert_not_called()
result = unittest.TextTestRunner().run(unittest.TestSuite([TestLoginLogic('test_wrong_password')]))
msg = f"Тесты {'успешны' if result.wasSuccessful() else 'провалены'}! Пройдено: {result.testsRun}, Ошибок: {len(result.errors)}, Провалов: {len(result.failures)}"
msg_box = QMessageBox()
msg_box.setWindowTitle("Результаты")
msg_box.setText(msg)
msg_box.exec()
app.exec()
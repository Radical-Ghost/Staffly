"""UI dialogs package."""

from staffly.ui.dialogs.employee_dialog import EmployeeDialog
from staffly.ui.dialogs.salary_structure_dialog import SalaryStructureDialog
from staffly.ui.dialogs.period_dialog import PeriodDialog
from staffly.ui.dialogs.attendance_dialog import AttendanceDialog
from staffly.ui.dialogs.company_selector_dialog import CompanySelectorDialog

__all__ = [
    "EmployeeDialog",
    "SalaryStructureDialog",
    "PeriodDialog",
    "AttendanceDialog",
    "CompanySelectorDialog",
]

"""Employee add/edit dialog."""

from datetime import date
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QTabWidget,
    QWidget,
    QComboBox,
)
from PySide6.QtCore import Qt, QDate

from staffly.database import get_db
from staffly.database.models import Employee
from staffly.database.repositories import EmployeeRepository, CompanyRepository
from staffly.ui.widgets.arrow_widgets import ArrowDateEdit, OptionalDateEdit


class EmployeeDialog(QDialog):
    """
    Dialog for adding/editing employee.
    
    Usage:
        # Add new
        dialog = EmployeeDialog(parent)
        
        # Edit existing
        dialog = EmployeeDialog(parent, employee_id=5)
    """

    def __init__(
        self,
        parent=None,
        employee_id: int = None,
        fixed_company_id: int | None = None,
        fixed_company_name: str | None = None,
    ):
        super().__init__(parent)
        self.employee_id = employee_id
        self.is_edit_mode = employee_id is not None
        self.fixed_company_id = fixed_company_id
        self.fixed_company_name = fixed_company_name
        self._setup_ui()
        
        if self.is_edit_mode:
            self._load_employee()

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Edit Employee" if self.is_edit_mode else "Add Employee")
        self.setMinimumSize(700, 600)
        self.resize(750, 650)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Tab widget for organized form
        tab_widget = QTabWidget()

        # ═══════════════════════════════════════════════════════════════════
        # TAB 1: Basic Info
        # ═══════════════════════════════════════════════════════════════════
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)

        # Company selector (required)
        self.cmb_company = QComboBox()
        if self.fixed_company_id:
            display_name = self.fixed_company_name or "Selected Company"
            self.cmb_company.addItem(display_name, self.fixed_company_id)
            self.cmb_company.setEnabled(False)
        else:
            self.cmb_company.addItem("-- Select Company --", None)
            self._load_companies()
        basic_layout.addRow("Company*:", self.cmb_company)

        self.txt_code = QLineEdit()
        self.txt_code.setPlaceholderText("e.g., EMP001")
        self.txt_code.setMaxLength(20)
        basic_layout.addRow("Employee Code*:", self.txt_code)

        self.txt_first_name = QLineEdit()
        self.txt_first_name.setMaxLength(50)
        basic_layout.addRow("First Name*:", self.txt_first_name)

        self.txt_middle_name = QLineEdit()
        self.txt_middle_name.setMaxLength(50)
        basic_layout.addRow("Middle Name:", self.txt_middle_name)

        self.txt_last_name = QLineEdit()
        self.txt_last_name.setMaxLength(50)
        basic_layout.addRow("Last Name*:", self.txt_last_name)

        # Gender dropdown
        self.cmb_gender = QComboBox()
        self.cmb_gender.addItem("-- Select Gender --", None)
        self.cmb_gender.addItem("Male", "Male")
        self.cmb_gender.addItem("Female", "Female")
        self.cmb_gender.addItem("Other", "Other")
        basic_layout.addRow("Gender:", self.cmb_gender)

        self.txt_designation = QLineEdit()
        self.txt_designation.setMaxLength(100)
        basic_layout.addRow("Designation*:", self.txt_designation)

        self.txt_department = QLineEdit()
        self.txt_department.setMaxLength(100)
        basic_layout.addRow("Department:", self.txt_department)

        self.txt_branch = QLineEdit()
        self.txt_branch.setMaxLength(100)
        self.txt_branch.setPlaceholderText("e.g., Head Office, Mumbai Branch")
        basic_layout.addRow("Branch:", self.txt_branch)

        tab_widget.addTab(basic_tab, "Basic Info")

        # ═══════════════════════════════════════════════════════════════════
        # TAB 2: Employment
        # ═══════════════════════════════════════════════════════════════════
        emp_tab = QWidget()
        emp_layout = QFormLayout(emp_tab)

        self.date_joining = ArrowDateEdit()
        self.date_joining.setDate(QDate.currentDate())
        self.date_joining.setDisplayFormat("dd-MM-yyyy")
        self.date_joining.setMinimumWidth(180)
        emp_layout.addRow("Date of Joining*:", self.date_joining)

        # Optional date with checkbox for "Not Set"
        self.date_leaving = OptionalDateEdit(label="Still Employed (No Leave Date)")
        emp_layout.addRow("Date of Leaving:", self.date_leaving)

        self.chk_active = QCheckBox("Employee is active")
        self.chk_active.setChecked(True)
        emp_layout.addRow("Status:", self.chk_active)

        tab_widget.addTab(emp_tab, "Employment")

        # ═══════════════════════════════════════════════════════════════════
        # TAB 3: Contact
        # ═══════════════════════════════════════════════════════════════════
        contact_tab = QWidget()
        contact_layout = QFormLayout(contact_tab)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("email@example.com")
        contact_layout.addRow("Email:", self.txt_email)

        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("+91 XXXXX XXXXX")
        contact_layout.addRow("Phone:", self.txt_phone)

        self.txt_address = QLineEdit()
        contact_layout.addRow("Address:", self.txt_address)

        tab_widget.addTab(contact_tab, "Contact")

        # ═══════════════════════════════════════════════════════════════════
        # TAB 4: Statutory
        # ═══════════════════════════════════════════════════════════════════
        stat_tab = QWidget()
        stat_layout = QFormLayout(stat_tab)

        self.txt_aadhar = QLineEdit()
        self.txt_aadhar.setPlaceholderText("12 digit Aadhar number")
        self.txt_aadhar.setMaxLength(12)
        stat_layout.addRow("Aadhar Number:", self.txt_aadhar)

        self.txt_pan = QLineEdit()
        self.txt_pan.setPlaceholderText("ABCDE1234F")
        self.txt_pan.setMaxLength(10)
        stat_layout.addRow("PAN Number:", self.txt_pan)

        self.txt_uan = QLineEdit()
        self.txt_uan.setPlaceholderText("UAN for PF")
        stat_layout.addRow("UAN (PF):", self.txt_uan)

        self.txt_esi = QLineEdit()
        self.txt_esi.setPlaceholderText("ESI Number")
        stat_layout.addRow("ESI Number:", self.txt_esi)

        tab_widget.addTab(stat_tab, "Statutory")

        layout.addWidget(tab_widget)

        # ═══════════════════════════════════════════════════════════════════
        # BUTTONS
        # ═══════════════════════════════════════════════════════════════════
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_style = """
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
                border: 2px solid transparent;
            }
            QPushButton:hover {
                border: 2px solid #333;
            }
            QPushButton:pressed {
                border: 2px solid #000;
            }
        """

        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setFixedSize(150, 50)
        self.btn_save.setStyleSheet(btn_style + """
            QPushButton { background-color: #4CAF50; color: white; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_save.clicked.connect(self._on_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(150, 50)
        self.btn_cancel.setStyleSheet(btn_style + """
            QPushButton { background-color: #9e9e9e; color: white; }
            QPushButton:hover { background-color: #757575; }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _load_companies(self):
        """Load companies into the dropdown."""
        db = get_db()
        with db.get_session() as session:
            repo = CompanyRepository(session)
            companies = repo.get_all_active()
            for company in companies:
                self.cmb_company.addItem(company.name, company.id)

    def _load_employee(self):
        """Load employee data into form."""
        db = get_db()
        with db.get_session() as session:
            repo = EmployeeRepository(session)
            emp = repo.get_by_id(self.employee_id)

            if emp:
                # Set company
                company_idx = self.cmb_company.findData(emp.company_id)
                if company_idx >= 0:
                    self.cmb_company.setCurrentIndex(company_idx)

                self.txt_code.setText(emp.employee_code)
                self.txt_first_name.setText(emp.first_name)
                self.txt_middle_name.setText(emp.middle_name or "")
                self.txt_last_name.setText(emp.last_name)
                
                # Set gender
                gender_idx = self.cmb_gender.findData(emp.gender)
                if gender_idx >= 0:
                    self.cmb_gender.setCurrentIndex(gender_idx)
                
                self.txt_designation.setText(emp.designation)
                self.txt_department.setText(emp.department or "")
                self.txt_branch.setText(emp.branch or "")
                self.txt_email.setText(emp.email or "")
                self.txt_phone.setText(emp.phone or "")
                self.txt_address.setText(emp.address or "")
                self.txt_aadhar.setText(emp.aadhar_number or "")
                self.txt_pan.setText(emp.pan_number or "")
                self.txt_uan.setText(emp.uan_number or "")
                self.txt_esi.setText(emp.esi_number or "")
                self.chk_active.setChecked(emp.is_active)

                self.date_joining.setDate(QDate(
                    emp.date_of_joining.year,
                    emp.date_of_joining.month,
                    emp.date_of_joining.day
                ))

                if emp.date_of_leaving:
                    self.date_leaving.setDate(QDate(
                        emp.date_of_leaving.year,
                        emp.date_of_leaving.month,
                        emp.date_of_leaving.day
                    ))
                else:
                    self.date_leaving.setNoDate(True)

    def _validate(self) -> bool:
        """Validate form data."""
        if not self.cmb_company.currentData():
            QMessageBox.warning(self, "Validation", "Please select a Company.")
            self.cmb_company.setFocus()
            return False

        if not self.txt_code.text().strip():
            QMessageBox.warning(self, "Validation", "Employee Code is required.")
            self.txt_code.setFocus()
            return False

        if not self.txt_first_name.text().strip():
            QMessageBox.warning(self, "Validation", "First Name is required.")
            self.txt_first_name.setFocus()
            return False

        if not self.txt_last_name.text().strip():
            QMessageBox.warning(self, "Validation", "Last Name is required.")
            self.txt_last_name.setFocus()
            return False

        if not self.txt_designation.text().strip():
            QMessageBox.warning(self, "Validation", "Designation is required.")
            self.txt_designation.setFocus()
            return False

        return True

    def _on_save(self):
        """Save employee data."""
        if not self._validate():
            return

        db = get_db()
        with db.get_session() as session:
            repo = EmployeeRepository(session)

            # Check for duplicate code (if new or code changed)
            code = self.txt_code.text().strip().upper()
            existing = repo.get_by_code(code)
            if existing and (not self.is_edit_mode or existing.id != self.employee_id):
                QMessageBox.warning(self, "Duplicate", f"Employee code '{code}' already exists.")
                return

            if self.is_edit_mode:
                emp = repo.get_by_id(self.employee_id)
            else:
                emp = Employee()

            # Set values
            emp.company_id = self.cmb_company.currentData()
            emp.employee_code = code
            emp.first_name = self.txt_first_name.text().strip()
            emp.middle_name = self.txt_middle_name.text().strip() or None
            emp.last_name = self.txt_last_name.text().strip()
            emp.gender = self.cmb_gender.currentData()
            emp.designation = self.txt_designation.text().strip()
            emp.department = self.txt_department.text().strip() or None
            emp.branch = self.txt_branch.text().strip() or None
            emp.email = self.txt_email.text().strip() or None
            emp.phone = self.txt_phone.text().strip() or None
            emp.address = self.txt_address.text().strip() or None
            emp.aadhar_number = self.txt_aadhar.text().strip() or None
            emp.pan_number = self.txt_pan.text().strip().upper() or None
            emp.uan_number = self.txt_uan.text().strip() or None
            emp.esi_number = self.txt_esi.text().strip() or None
            emp.is_active = self.chk_active.isChecked()

            # Dates
            qdate = self.date_joining.date()
            emp.date_of_joining = date(qdate.year(), qdate.month(), qdate.day())

            # Handle optional leaving date
            qdate_leave = self.date_leaving.date()
            if qdate_leave is not None:
                emp.date_of_leaving = date(qdate_leave.year(), qdate_leave.month(), qdate_leave.day())
            else:
                emp.date_of_leaving = None

            if not self.is_edit_mode:
                repo.create(emp)

            repo.commit()

        self.accept()

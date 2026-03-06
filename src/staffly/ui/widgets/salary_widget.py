"""Salary structure management widget."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QGroupBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence

from staffly.database import get_db
from staffly.database.repositories import EmployeeRepository, SalaryStructureRepository
from staffly.ui.dialogs.salary_structure_dialog import SalaryStructureDialog
from PySide6.QtWidgets import QComboBox


class SalaryWidget(QWidget):
    """
    Salary structure management page.
    
    Features:
    - Employee selector dropdown
    - Salary structure history for selected employee
    - Add, Edit salary structure
    - Ctrl+Scroll or Ctrl+Plus/Minus to zoom table
    """

    def __init__(self, selected_company_id: int, selected_company_name: str):
        super().__init__()
        self.selected_company_id = selected_company_id
        self.selected_company_name = selected_company_name
        self._table_font_size = 14
        self._setup_ui()
        self._setup_zoom_shortcuts()
        self._load_employees()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 8, 10, 10)

        # ═══════════════════════════════════════════════════════════════════
        # EMPLOYEE SELECTOR
        # ═══════════════════════════════════════════════════════════════════
        selector_group = QGroupBox("Select Employee")
        selector_layout = QHBoxLayout(selector_group)

        selector_label = QLabel("Employee:")
        self.employee_combo = QComboBox()
        self.employee_combo.setMinimumWidth(300)
        self.employee_combo.currentIndexChanged.connect(self._on_employee_changed)

        scope_label = QLabel(f"Company: {self.selected_company_name}")
        scope_label.setStyleSheet("font-weight: 600;")

        # Button style - 150x50
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
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
                border: none;
            }
        """

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setFixedSize(150, 50)
        self.btn_refresh.setStyleSheet(btn_style + """
            QPushButton { background-color: #607D8B; color: white; }
            QPushButton:hover { background-color: #546E7A; }
        """)
        self.btn_refresh.clicked.connect(self._load_employees)

        selector_layout.addWidget(selector_label)
        selector_layout.addWidget(self.employee_combo)
        selector_layout.addSpacing(12)
        selector_layout.addWidget(scope_label)
        selector_layout.addStretch()
        selector_layout.addWidget(self.btn_refresh)

        layout.addWidget(selector_group)

        # ═══════════════════════════════════════════════════════════════════
        # CURRENT SALARY INFO
        # ═══════════════════════════════════════════════════════════════════
        self.current_salary_group = QGroupBox("Current Salary Structure")
        current_layout = QHBoxLayout(self.current_salary_group)

        self.lbl_basic = QLabel("Basic: ₹0")
        self.lbl_hra = QLabel("HRA: ₹0")
        self.lbl_gross = QLabel("Gross: ₹0")
        self.lbl_effective = QLabel("Effective From: -")

        current_layout.addWidget(self.lbl_basic)
        current_layout.addWidget(self.lbl_hra)
        current_layout.addWidget(self.lbl_gross)
        current_layout.addStretch()
        current_layout.addWidget(self.lbl_effective)

        layout.addWidget(self.current_salary_group)

        # ═══════════════════════════════════════════════════════════════════
        # BUTTONS
        # ═══════════════════════════════════════════════════════════════════
        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton("➕ Add New Structure")
        self.btn_add.setFixedSize(150, 50)
        self.btn_add.setStyleSheet(btn_style + """
            QPushButton { background-color: #4CAF50; color: white; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_add.clicked.connect(self._on_add)
        self.btn_add.setEnabled(False)

        self.btn_edit = QPushButton("✏️ Edit Selected")
        self.btn_edit.setFixedSize(150, 50)
        self.btn_edit.setStyleSheet(btn_style + """
            QPushButton { background-color: #2196F3; color: white; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_edit.setEnabled(False)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # ═══════════════════════════════════════════════════════════════════
        # SALARY HISTORY TABLE
        # ═══════════════════════════════════════════════════════════════════
        history_group = QGroupBox("Salary Structure History")
        history_layout = QVBoxLayout(history_group)

        self.table = QTableWidget()
        self.table.setObjectName("salaryTable")
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Effective From", "Effective To", "Basic", "HRA", 
            "Bonus", "CCA", "Other", "PF (Employer)", "Gross"
        ])

        # Table settings
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(35)

        # Table styling
        self._apply_table_zoom()

        # Hide ID column
        self.table.setColumnHidden(0, True)

        # Column widths
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # Connect signals
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_edit)

        history_layout.addWidget(self.table)
        layout.addWidget(history_group)

    def _load_employees(self):
        """Load employees into combo box."""
        self.employee_combo.clear()
        self.employee_combo.addItem("-- Select Employee --", None)

        db = get_db()
        with db.get_session() as session:
            repo = EmployeeRepository(session)
            employees = repo.get_active_by_company(self.selected_company_id)

            for emp in employees:
                self.employee_combo.addItem(
                    f"{emp.employee_code} - {emp.full_name}",
                    emp.id
                )

    def _on_employee_changed(self, index: int):
        """Handle employee selection change."""
        emp_id = self.employee_combo.currentData()
        self.btn_add.setEnabled(emp_id is not None)
        self._load_salary_structures(emp_id)

    def _load_salary_structures(self, employee_id: int | None):
        """Load salary structures for selected employee."""
        self.table.setRowCount(0)
        self._clear_current_info()

        if not employee_id:
            return

        db = get_db()
        with db.get_session() as session:
            repo = SalaryStructureRepository(session)
            structures = repo.get_by_employee_id(employee_id)

            for i, struct in enumerate(structures):
                row = self.table.rowCount()
                self.table.insertRow(row)

                self.table.setItem(row, 0, QTableWidgetItem(str(struct.id)))
                self.table.setItem(row, 1, QTableWidgetItem(
                    struct.effective_from.strftime("%d-%m-%Y")
                ))
                self.table.setItem(row, 2, QTableWidgetItem(
                    struct.effective_to.strftime("%d-%m-%Y") if struct.effective_to else "Current"
                ))
                self.table.setItem(row, 3, QTableWidgetItem(f"₹{struct.basic_salary:,.2f}"))
                self.table.setItem(row, 4, QTableWidgetItem(f"₹{struct.hra:,.2f}"))
                self.table.setItem(row, 5, QTableWidgetItem(f"₹{struct.bonus:,.2f}"))
                self.table.setItem(row, 6, QTableWidgetItem(f"₹{struct.cca:,.2f}"))
                self.table.setItem(row, 7, QTableWidgetItem(f"₹{struct.other_allowance:,.2f}"))
                self.table.setItem(row, 8, QTableWidgetItem(f"₹{struct.pf_employer:,.2f}"))
                self.table.setItem(row, 9, QTableWidgetItem(f"₹{struct.gross_salary:,.2f}"))

                # Highlight current structure
                if struct.effective_to is None:
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(Qt.lightGray)

                    # Update current info
                    self.lbl_basic.setText(f"Basic: ₹{struct.basic_salary:,.2f}")
                    self.lbl_hra.setText(f"HRA: ₹{struct.hra:,.2f}")
                    self.lbl_gross.setText(f"Gross: ₹{struct.gross_salary:,.2f}")
                    self.lbl_effective.setText(
                        f"Effective From: {struct.effective_from.strftime('%d-%m-%Y')}"
                    )

    def _clear_current_info(self):
        """Clear current salary info labels."""
        self.lbl_basic.setText("Basic: ₹0")
        self.lbl_hra.setText("HRA: ₹0")
        self.lbl_gross.setText("Gross: ₹0")
        self.lbl_effective.setText("Effective From: -")

    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.table.selectedItems()) > 0
        self.btn_edit.setEnabled(has_selection)

    def _get_selected_structure_id(self) -> int | None:
        """Get the ID of the selected salary structure."""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            id_item = self.table.item(row, 0)
            if id_item:
                return int(id_item.text())
        return None

    def _on_add(self):
        """Open dialog to add new salary structure."""
        emp_id = self.employee_combo.currentData()
        if emp_id:
            dialog = SalaryStructureDialog(self, employee_id=emp_id)
            if dialog.exec():
                self._load_salary_structures(emp_id)

    def _on_edit(self):
        """Open dialog to edit selected salary structure."""
        struct_id = self._get_selected_structure_id()
        emp_id = self.employee_combo.currentData()
        if struct_id and emp_id:
            dialog = SalaryStructureDialog(self, employee_id=emp_id, structure_id=struct_id)
            if dialog.exec():
                self._load_salary_structures(emp_id)

    def _setup_zoom_shortcuts(self):
        """Setup keyboard shortcuts for zooming."""
        zoom_in = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in.activated.connect(self._zoom_in)
        zoom_in2 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in2.activated.connect(self._zoom_in)
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(self._zoom_out)
        zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_reset.activated.connect(self._zoom_reset)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming with Ctrl key."""
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def _zoom_in(self):
        if self._table_font_size < 24:
            self._table_font_size += 2
            self._apply_table_zoom()

    def _zoom_out(self):
        if self._table_font_size > 10:
            self._table_font_size -= 2
            self._apply_table_zoom()

    def _zoom_reset(self):
        self._table_font_size = 14
        self._apply_table_zoom()

    def _apply_table_zoom(self):
        self.table.setStyleSheet(f"""
            QTableWidget {{
                font-size: {self._table_font_size}px;
                gridline-color: #ddd;
            }}
            QTableWidget::item {{
                padding: 6px;
            }}
            QHeaderView::section {{
                font-size: {self._table_font_size}px;
                font-weight: bold;
                padding: 8px;
                background-color: #f5f5f5;
                border: 1px solid #ddd;
            }}
        """)
        self.table.verticalHeader().setDefaultSectionSize(int(self._table_font_size * 2.5))

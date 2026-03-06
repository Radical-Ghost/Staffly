"""Employee management widget - list, add, edit, delete employees."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
    QLabel,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QComboBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from staffly.database import get_db
from staffly.database.repositories import EmployeeRepository
from staffly.ui.dialogs.employee_dialog import EmployeeDialog


class EmployeeWidget(QWidget):
    """
    Employee management page.
    
    Features:
    - Employee list table
    - Search by name/code
    - Filter by company
    - Filter by status (Active/Inactive/All)
    - Add, Edit, Delete buttons
    - Ctrl+Scroll or Ctrl+Plus/Minus to zoom table
    """

    def __init__(self, selected_company_id: int, selected_company_name: str):
        super().__init__()
        self.selected_company_id = selected_company_id
        self.selected_company_name = selected_company_name
        self._table_font_size = 14  # Base font size for table
        self._setup_ui()
        self._setup_zoom_shortcuts()
        self._load_employees()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 8, 10, 10)

        # ═══════════════════════════════════════════════════════════════════
        # TOP BAR: Search + Filter + Buttons
        # ═══════════════════════════════════════════════════════════════════
        top_bar = QHBoxLayout()
        top_bar.setSpacing(15)

        # Search
        search_label = QLabel("🔍 Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or code...")
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self._on_search)

        # Company scope label
        company_label = QLabel(f"🏢 Company: {self.selected_company_name}")

        # Status filter
        filter_label = QLabel("📋 Status:")
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Inactive"])
        self.status_filter.setCurrentIndex(1)  # Default to Active
        self.status_filter.setMinimumWidth(100)
        self.status_filter.currentIndexChanged.connect(self._load_employees)

        # Button style - 150x50 exact size
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

        # Buttons with fixed size 150x50
        self.btn_add = QPushButton("➕ Add Employee")
        self.btn_add.setFixedSize(150, 50)
        self.btn_add.setStyleSheet(btn_style + """
            QPushButton { background-color: #4CAF50; color: white; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_add.clicked.connect(self._on_add)

        self.btn_edit = QPushButton("✏️ Edit")
        self.btn_edit.setFixedSize(150, 50)
        self.btn_edit.setStyleSheet(btn_style + """
            QPushButton { background-color: #2196F3; color: white; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_edit.setEnabled(False)

        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_delete.setFixedSize(150, 50)
        self.btn_delete.setStyleSheet(btn_style + """
            QPushButton { background-color: #f44336; color: white; }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_delete.setEnabled(False)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setFixedSize(150, 50)
        self.btn_refresh.setStyleSheet(btn_style + """
            QPushButton { background-color: #607D8B; color: white; }
            QPushButton:hover { background-color: #546E7A; }
        """)
        self.btn_refresh.clicked.connect(self._load_employees)

        # Add to top bar
        top_bar.addWidget(search_label)
        top_bar.addWidget(self.search_input)
        top_bar.addSpacing(15)
        top_bar.addWidget(company_label)
        top_bar.addSpacing(15)
        top_bar.addWidget(filter_label)
        top_bar.addWidget(self.status_filter)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_add)
        top_bar.addWidget(self.btn_edit)
        top_bar.addWidget(self.btn_delete)
        top_bar.addWidget(self.btn_refresh)

        layout.addLayout(top_bar)

        # ═══════════════════════════════════════════════════════════════════
        # EMPLOYEE TABLE
        # ═══════════════════════════════════════════════════════════════════
        self.table = QTableWidget()
        self.table.setObjectName("employeeTable")
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Code", "Name", "Company", "Designation", "Department", "Joining Date", "Status"
        ])

        # Table styling - scaled proportionally
        self.table.setStyleSheet("""
            QTableWidget {
                font-size: 14px;
                gridline-color: #ddd;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QHeaderView::section {
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #f5f5f5;
                border: 1px solid #ddd;
            }
        """)

        # Table settings
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(35)  # Row height

        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Code
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Name
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Company
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Designation
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Department
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Joining Date
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Status

        # Hide ID column (used internally)
        self.table.setColumnHidden(0, True)

        # Connect selection change
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_edit)

        layout.addWidget(self.table)

        # ═══════════════════════════════════════════════════════════════════
        # BOTTOM STATUS
        # ═══════════════════════════════════════════════════════════════════
        self.status_label = QLabel("0 employees")
        layout.addWidget(self.status_label)

    def _load_employees(self):
        """Load employees from database into table."""
        self.table.setRowCount(0)

        db = get_db()
        with db.get_session() as session:
            repo = EmployeeRepository(session)

            # Get based on filter
            filter_status = self.status_filter.currentText()
            company_id = self.selected_company_id

            if filter_status == "Active":
                if company_id:
                    employees = repo.get_active_by_company(company_id)
                else:
                    employees = repo.get_all_active()
            elif filter_status == "Inactive":
                if company_id:
                    employees = [e for e in repo.get_by_company(company_id) if not e.is_active]
                else:
                    employees = [e for e in repo.get_all() if not e.is_active]
            else:
                if company_id:
                    employees = repo.get_by_company(company_id)
                else:
                    employees = repo.get_all()

            # Populate table
            for emp in employees:
                row = self.table.rowCount()
                self.table.insertRow(row)

                self.table.setItem(row, 0, QTableWidgetItem(str(emp.id)))
                self.table.setItem(row, 1, QTableWidgetItem(emp.employee_code))
                self.table.setItem(row, 2, QTableWidgetItem(emp.full_name))
                self.table.setItem(row, 3, QTableWidgetItem(emp.company.name if emp.company else ""))
                self.table.setItem(row, 4, QTableWidgetItem(emp.designation))
                self.table.setItem(row, 5, QTableWidgetItem(emp.department or ""))
                self.table.setItem(row, 6, QTableWidgetItem(
                    emp.date_of_joining.strftime("%d-%m-%Y")
                ))
                
                status_item = QTableWidgetItem("Active" if emp.is_active else "Inactive")
                status_item.setForeground(
                    Qt.darkGreen if emp.is_active else Qt.darkRed
                )
                self.table.setItem(row, 7, status_item)

        # Update status
        count = self.table.rowCount()
        self.status_label.setText(f"{count} employee{'s' if count != 1 else ''}")

    def _on_search(self, text: str):
        """Filter table based on search text."""
        for row in range(self.table.rowCount()):
            match = False
            # Search in Code and Name columns
            for col in [1, 2]:
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.table.selectedItems()) > 0
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _get_selected_employee_id(self) -> int | None:
        """Get the ID of the selected employee."""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            id_item = self.table.item(row, 0)
            if id_item:
                return int(id_item.text())
        return None

    def _setup_zoom_shortcuts(self):
        """Setup keyboard shortcuts for zooming."""
        # Ctrl+Plus to zoom in
        zoom_in = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in.activated.connect(self._zoom_in)
        
        # Ctrl+Equal (for keyboards where + needs shift)
        zoom_in2 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in2.activated.connect(self._zoom_in)
        
        # Ctrl+Minus to zoom out
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(self._zoom_out)
        
        # Ctrl+0 to reset zoom
        zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_reset.activated.connect(self._zoom_reset)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming with Ctrl key."""
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def _zoom_in(self):
        """Increase table font size."""
        if self._table_font_size < 24:
            self._table_font_size += 2
            self._apply_table_zoom()

    def _zoom_out(self):
        """Decrease table font size."""
        if self._table_font_size > 10:
            self._table_font_size -= 2
            self._apply_table_zoom()

    def _zoom_reset(self):
        """Reset table font size to default."""
        self._table_font_size = 14
        self._apply_table_zoom()

    def _apply_table_zoom(self):
        """Apply current zoom level to table."""
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
        # Adjust row height based on font size
        row_height = int(self._table_font_size * 2.5)
        self.table.verticalHeader().setDefaultSectionSize(row_height)

    def _on_add(self):
        """Open dialog to add new employee."""
        dialog = EmployeeDialog(
            self,
            fixed_company_id=self.selected_company_id,
            fixed_company_name=self.selected_company_name,
        )
        if dialog.exec():
            self._load_employees()

    def _on_edit(self):
        """Open dialog to edit selected employee."""
        emp_id = self._get_selected_employee_id()
        if emp_id:
            dialog = EmployeeDialog(self, employee_id=emp_id)
            if dialog.exec():
                self._load_employees()

    def _on_delete(self):
        """Delete selected employee."""
        emp_id = self._get_selected_employee_id()
        if not emp_id:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this employee?\n\n"
            "This will also delete all salary structures and payroll records.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            db = get_db()
            with db.get_session() as session:
                repo = EmployeeRepository(session)
                if repo.delete_by_id(emp_id):
                    repo.commit()
                    self._load_employees()
                    QMessageBox.information(self, "Deleted", "Employee deleted successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete employee.")

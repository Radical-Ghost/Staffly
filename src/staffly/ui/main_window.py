"""Main application window with tab navigation."""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QStatusBar,
    QRadioButton,
    QButtonGroup,
    QPushButton,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt, QSettings, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction, QActionGroup

from staffly.config import get_config
from staffly.ui.theme import get_theme, load_theme, toggle_theme, get_theme_colors, is_dark_theme
from staffly.ui.widgets.employee_widget import EmployeeWidget
from staffly.ui.widgets.salary_widget import SalaryWidget
from staffly.ui.widgets.attendance_widget import AttendanceWidget
from staffly.ui.widgets.payroll_widget import PayrollWidget
from staffly.ui.widgets.reports_widget import ReportsWidget


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Contains:
    - Menu bar (File, View, Help)
    - Tab widget with 4 tabs (Employees, Salary, Payroll, Reports)
    - Status bar
    """

    def __init__(self, companies: list[tuple[int, str, str]]):
        super().__init__()
        self.config = get_config()
        self.settings = QSettings("Staffly", "Staffly")
        self.available_companies = companies
        self.selected_company_id: int | None = None
        self.selected_company_code: str = ""
        self.selected_company_name: str = ""
        self._splash_animating = False
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()

    def _setup_ui(self):
        """Initialize the main UI components."""
        # Window properties
        self.setWindowTitle(self.config.window_title)
        self.setMinimumSize(1000, 700)
        self.resize(self.config.window_width, self.config.window_height)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with modern spacing
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainTabWidget")
        self.tab_widget.setVisible(False)
        main_layout.addWidget(self.tab_widget)

        # In-app splash selector overlay
        self._setup_company_splash()

    def _setup_company_splash(self):
        """Create themed startup company splash selector."""
        # Get current theme colors
        colors = get_theme_colors()
        
        self.splash_overlay = QWidget(self.centralWidget())
        self.splash_overlay.setStyleSheet(f"""
            QWidget {{
                background-color: {colors.background};
                border: none;
            }}
        """)

        layout = QVBoxLayout(self.splash_overlay)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.addStretch(1)
        
        # Card container for content
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {colors.surface};
                border: 1px solid {colors.border};
                border-radius: 12px;
            }}
        """)
        card.setMaximumWidth(500)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(24)

        # Logo / Title
        title = QLabel("Staffly")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: 700; 
            color: {colors.primary};
            border: none;
            background: transparent;
        """)
        card_layout.addWidget(title)

        subtitle = QLabel("Select your company to continue")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"""
            font-size: 14px; 
            color: {colors.text_secondary};
            border: none;
            background: transparent;
        """)
        card_layout.addWidget(subtitle)

        # Radio button styling with current theme colors
        radio_style = f"""
            QRadioButton {{
                spacing: 12px;
                font-size: 15px;
                padding: 12px 16px;
                color: {colors.text_primary};
                background: transparent;
                border: none;
            }}
            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid {colors.border};
                background: {colors.surface_alt};
            }}
            QRadioButton::indicator:hover {{
                border-color: {colors.primary};
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid {colors.primary};
                background: {colors.primary};
            }}
        """

        radio_row = QHBoxLayout()
        radio_row.addStretch()
        self.company_group = QButtonGroup(self)
        self.company_group.setExclusive(True)

        for index, (company_id, company_code, company_name) in enumerate(self.available_companies):
            label = company_code or company_name
            radio = QRadioButton(label)
            radio.setProperty("company_id", company_id)
            radio.setProperty("company_name", company_name)
            radio.setStyleSheet(radio_style)
            self.company_group.addButton(radio)
            radio_row.addWidget(radio)
            if index == 0:
                radio.setChecked(True)

        radio_row.addStretch()
        card_layout.addLayout(radio_row)

        # Primary button with theme colors
        colors = get_theme_colors()  # Get fresh colors
        self.btn_select_company = QPushButton("Continue")
        self.btn_select_company.setFixedSize(160, 44)
        self.btn_select_company.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_company.setStyleSheet(f"""
            QPushButton {{
                font-size: 15px;
                font-weight: 600;
                color: {colors.selection_text};
                background-color: {colors.primary};
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {colors.primary_hover};
            }}
            QPushButton:pressed {{
                background-color: {colors.primary};
            }}
        """)
        self.btn_select_company.clicked.connect(self._on_select_company)
        card_layout.addWidget(self.btn_select_company, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Add card to layout
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

        self.splash_overlay.raise_()
        self.splash_overlay.setGeometry(self.centralWidget().rect())

        self.splash_overlay.raise_()
        self.splash_overlay.setGeometry(self.centralWidget().rect())

    def _on_select_company(self):
        """Apply selected company and reveal app by moving splash up."""
        selected_button = self.company_group.checkedButton()
        if not selected_button:
            QMessageBox.warning(self, "Select Company", "Please select a company.")
            return

        if self._splash_animating:
            return

        self.selected_company_id = selected_button.property("company_id")
        self.selected_company_code = selected_button.text()
        self.selected_company_name = selected_button.property("company_name")
        self._create_tabs()
        self.tab_widget.setVisible(True)
        if hasattr(self, "switch_company_action"):
            self.switch_company_action.setVisible(True)
        self.setWindowTitle(f"{self.config.window_title} - {self.selected_company_name}")
        self.statusbar.showMessage(f"Ready - Company: {self.selected_company_name}")

        self._splash_animating = True
        self.btn_select_company.setEnabled(False)
        start_pos = self.splash_overlay.pos()
        end_pos = QPoint(start_pos.x(), -self.splash_overlay.height())

        self.splash_anim = QPropertyAnimation(self.splash_overlay, b"pos")
        self.splash_anim.setDuration(380)
        self.splash_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.splash_anim.setStartValue(start_pos)
        self.splash_anim.setEndValue(end_pos)
        self.splash_anim.finished.connect(self._on_splash_animation_finished)
        self.splash_anim.start()

    def _on_splash_animation_finished(self):
        """Handle splash animation completion."""
        self.splash_overlay.hide()
        self._splash_animating = False

    def _create_tabs(self):
        """Create and add all tabs to the tab widget."""
        while self.tab_widget.count() > 0:
            widget = self.tab_widget.widget(0)
            self.tab_widget.removeTab(0)
            if widget is not None:
                widget.deleteLater()

        # Tab 1: Employees
        self.employee_widget = EmployeeWidget(
            selected_company_id=self.selected_company_id,
            selected_company_name=self.selected_company_name,
        )
        self.tab_widget.addTab(self.employee_widget, "👤 Employees")

        # Tab 2: Salary Structures
        self.salary_widget = SalaryWidget(
            selected_company_id=self.selected_company_id,
            selected_company_name=self.selected_company_name,
        )
        self.tab_widget.addTab(self.salary_widget, "💰 Salary")

        # Tab 3: Attendance
        self.attendance_widget = AttendanceWidget(
            selected_company_id=self.selected_company_id,
            selected_company_name=self.selected_company_name,
        )
        self.tab_widget.addTab(self.attendance_widget, "📅 Attendance")

        # Tab 4: Payroll
        self.payroll_widget = PayrollWidget(
            selected_company_id=self.selected_company_id,
            selected_company_name=self.selected_company_name,
        )
        self.tab_widget.addTab(self.payroll_widget, "📊 Payroll")

        # Tab 5: Reports
        self.reports_widget = ReportsWidget(
            selected_company_id=self.selected_company_id,
            selected_company_name=self.selected_company_name,
            selected_company_code=self.selected_company_code,
        )
        self.tab_widget.addTab(self.reports_widget, "📄 Reports")

    def _on_back_to_company_selection(self):
        """Return to company selector without restarting app."""
        if self._splash_animating:
            return

        self.tab_widget.setVisible(False)
        if hasattr(self, "switch_company_action"):
            self.switch_company_action.setVisible(False)
        self.setWindowTitle(self.config.window_title)
        self.statusbar.showMessage("Select company to continue")

        self._splash_animating = False
        self.btn_select_company.setEnabled(True)
        self.splash_overlay.setGeometry(self.centralWidget().rect())
        self.splash_overlay.move(0, 0)
        self.splash_overlay.show()
        self.splash_overlay.raise_()

    def _setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        # Backup action
        backup_action = QAction("&Backup Database...", self)
        backup_action.setShortcut("Ctrl+B")
        backup_action.triggered.connect(self._on_backup)
        file_menu.addAction(backup_action)

        # Restore action
        restore_action = QAction("&Restore from Backup...", self)
        restore_action.triggered.connect(self._on_restore)
        file_menu.addAction(restore_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View Menu
        view_menu = menubar.addMenu("&View")

        # Theme toggle action
        self.theme_action = QAction("🌙 Dark Mode" if is_dark_theme() else "☀️ Light Mode", self)
        self.theme_action.setShortcut("Ctrl+T")
        self.theme_action.triggered.connect(self._on_toggle_theme)
        view_menu.addAction(self.theme_action)

        view_menu.addSeparator()

        # Scale submenu
        scale_menu = view_menu.addMenu("🔍 Scale")
        scale_group = QActionGroup(self)
        scale_group.setExclusive(True)
        
        # Get current scale factor
        current_scale = self.settings.value("ui_scale_factor", 1.0, type=float)
        
        # Scale options: 50% to 150% in 10% increments
        scale_options = [
            ("50%", 0.50),
            ("60%", 0.60),
            ("70%", 0.70),
            ("80%", 0.80),
            ("90%", 0.90),
            ("100% (Default)", 1.00),
            ("110%", 1.10),
            ("120%", 1.20),
            ("130%", 1.30),
            ("140%", 1.40),
            ("150%", 1.50),
        ]
        
        self.scale_actions = {}
        for label, value in scale_options:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(abs(current_scale - value) < 0.01)
            action.setData(value)
            action.triggered.connect(lambda checked, v=value: self._on_scale_changed(v))
            scale_group.addAction(action)
            scale_menu.addAction(action)
            self.scale_actions[value] = action

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

        # Direct menu action on same row as File/View/Help
        self.switch_company_action = QAction("Switch Company", self)
        self.switch_company_action.triggered.connect(self._on_back_to_company_selection)
        self.switch_company_action.setVisible(False)
        menubar.addAction(self.switch_company_action)

    def _setup_statusbar(self):
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Select company to continue")

    def resizeEvent(self, event):
        """Keep splash overlay aligned with window until dismissed."""
        super().resizeEvent(event)
        if hasattr(self, "splash_overlay") and self.splash_overlay.isVisible() and not self._splash_animating:
            self.splash_overlay.setGeometry(self.centralWidget().rect())

    def _on_backup(self):
        """Handle backup action."""
        from staffly.services.backup_service import get_backup_service
        
        try:
            backup_service = get_backup_service()
            backup_path = backup_service.create_backup()
            
            QMessageBox.information(
                self,
                "Backup Complete",
                f"Database backed up successfully!\n\n"
                f"Location:\n{backup_path}\n\n"
                f"Total backups: {len(backup_service.list_backups())}"
            )
            self.show_status("Backup created successfully")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Backup Failed",
                f"Failed to create backup:\n{str(e)}"
            )

    def _on_restore(self):
        """Handle restore from backup action."""
        from PySide6.QtWidgets import QInputDialog
        from staffly.services.backup_service import get_backup_service
        
        try:
            backup_service = get_backup_service()
            backups = backup_service.list_backups()
            
            if not backups:
                QMessageBox.information(
                    self,
                    "No Backups",
                    "No backup files found."
                )
                return
            
            # Create list of backup options
            options = [
                f"{b['name']} ({b['created'].strftime('%Y-%m-%d %H:%M')})"
                for b in backups
            ]
            
            item, ok = QInputDialog.getItem(
                self,
                "Restore from Backup",
                "Select backup to restore:",
                options,
                0,
                False
            )
            
            if ok and item:
                idx = options.index(item)
                backup_path = backups[idx]['path']
                
                # Confirm
                reply = QMessageBox.question(
                    self,
                    "Confirm Restore",
                    f"Are you sure you want to restore from:\n{backup_path.name}\n\n"
                    "WARNING: This will overwrite the current database!\n"
                    "A safety backup will be created first.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    backup_service.restore_backup(backup_path)
                    QMessageBox.information(
                        self,
                        "Restore Complete",
                        "Database restored successfully!\n\n"
                        "Please restart the application."
                    )
                    self.show_status("Database restored - please restart")
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                "Restore Failed",
                f"Failed to restore backup:\n{str(e)}"
            )

    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Staffly",
            f"<h2>Staffly</h2>"
            f"<p>Version {self.config.app_version}</p>"
            f"<p>Desktop Payroll Management System</p>"
            f"<p>© 2026 All rights reserved</p>"
        )

    def show_status(self, message: str, timeout: int = 5000):
        """Show a message in the status bar."""
        self.statusbar.showMessage(message, timeout)

    def _on_scale_changed(self, scale_factor: float):
        """Handle scale factor change - applies immediately."""
        # Note: Scale factor is saved but doesn't affect QSS-based theming
        self.settings.setValue("ui_scale_factor", scale_factor)
        self.settings.sync()
        self.show_status(f"Scale set to {int(scale_factor * 100)}% (restart required)")

    def _on_toggle_theme(self):
        """Toggle between light and dark mode."""
        toggle_theme()
        # Update menu text
        is_dark = is_dark_theme()
        self.theme_action.setText("🌙 Dark Mode" if is_dark else "☀️ Light Mode")
        self.show_status(f"Switched to {'Dark' if is_dark else 'Light'} Mode")
        # Update splash overlay colors if still visible
        if hasattr(self, 'splash_overlay') and self.splash_overlay.isVisible():
            self._update_splash_colors()

    def _update_splash_colors(self):
        """Update splash screen colors when theme changes."""
        colors = get_theme_colors()
        self.splash_overlay.setStyleSheet(f"""
            QWidget {{
                background-color: {colors.background};
                border: none;
            }}
        """)

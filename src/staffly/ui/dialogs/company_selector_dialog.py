"""Company selector splash dialog shown at startup."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QButtonGroup,
    QRadioButton,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint


class CompanySelectorDialog(QDialog):
    """Splash-style dialog to select active company context."""

    def __init__(self, companies: list[tuple[int, str, str]], parent=None):
        super().__init__(parent)
        self._companies = companies
        self.selected_company_id: int | None = None
        self.selected_company_name: str | None = None
        self._is_animating = False
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Select Company")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setModal(True)
        self.setFixedSize(420, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Select Company")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Choose company scope for this session")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px; color: #666;")
        layout.addWidget(subtitle)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        radio_style = """
            QRadioButton {
                spacing: 10px;
                font-size: 15px;
                padding: 6px 4px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #666;
                background: white;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #1976D2;
                background: #1976D2;
            }
        """

        for index, (company_id, company_code, company_name) in enumerate(self._companies):
            label = company_code or company_name
            radio = QRadioButton(label)
            radio.setStyleSheet(radio_style)
            radio.setProperty("company_id", company_id)
            radio.setProperty("company_name", company_name)
            self.button_group.addButton(radio)
            layout.addWidget(radio)
            if index == 0:
                radio.setChecked(True)

        layout.addStretch()

        self.btn_select = QPushButton("Select")
        self.btn_select.setFixedSize(140, 44)
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.setStyleSheet(
            """
            QPushButton {
                font-size: 14px;
                font-weight: 700;
                color: white;
                background-color: #1976D2;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            """
        )
        self.btn_select.clicked.connect(self._on_select)
        layout.addWidget(self.btn_select, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _on_select(self):
        selected_button = self.button_group.checkedButton()
        if not selected_button:
            QMessageBox.warning(self, "Select Company", "Please select a company to continue.")
            return

        self.selected_company_id = selected_button.property("company_id")
        self.selected_company_name = selected_button.property("company_name")

        if self._is_animating:
            return
        self._is_animating = True
        self.btn_select.setEnabled(False)

        start = self.pos()
        end = QPoint(start.x(), start.y() - 90)
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(320)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.finished.connect(self.accept)
        self._anim.start()

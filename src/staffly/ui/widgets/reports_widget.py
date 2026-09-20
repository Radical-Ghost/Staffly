"""Reports widget - generate salary slips and analytics."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QFileDialog,
    QProgressDialog,
    QFrame,
    QSizePolicy,
    QScrollArea,
    QComboBox,
)
from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor, QPen, QBrush
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
    QCategoryAxis,
)

from staffly.database import get_db
from staffly.database.repositories import (
    PayrollPeriodRepository,
    MonthlyPayrollRepository,
    LeaveBalanceRepository,
)
from staffly.services.payroll_service import get_financial_year
from staffly.reports import SalarySlipGenerator
from staffly.ui.theme import get_theme


class ReportsWidget(QWidget):
    """Reports page — salary slip generation and spend analytics."""

    def __init__(
        self,
        selected_company_id: int,
        selected_company_name: str,
        selected_company_code: str = "",
    ):
        super().__init__()
        self.selected_company_id = selected_company_id
        self.selected_company_name = selected_company_name
        self.selected_company_code = selected_company_code
        self._setup_ui()
        self._load_periods()
        self._refresh_chart()

    # ─────────────────────────────────────────────────────────────────────────
    # UI SETUP
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        """Build the page layout."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        # Wrap everything in a scroll area so the chart never gets clipped
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner_widget = QWidget()
        layout = QVBoxLayout(inner_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        scroll.setWidget(inner_widget)
        outer.addWidget(scroll)

        # ── Header card ──────────────────────────────────────────────────────
        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("Reports")
        title.setObjectName("cardHeader")
        title_row.addWidget(title)
        title_row.addStretch()
        badge = QLabel(self.selected_company_name)
        badge.setObjectName("badge")
        title_row.addWidget(badge)
        header_layout.addLayout(title_row)

        # Controls row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)

        ctrl_row.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.setMinimumWidth(220)
        self.period_combo.setFixedHeight(36)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        ctrl_row.addWidget(self.period_combo)

        ctrl_row.addWidget(QLabel("Employee:"))
        self.employee_combo = QComboBox()
        self.employee_combo.setMinimumWidth(280)
        self.employee_combo.setFixedHeight(36)
        self.employee_combo.addItem("-- All Employees --", None)
        ctrl_row.addWidget(self.employee_combo)

        ctrl_row.addStretch()

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setObjectName("secondaryButton")
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.clicked.connect(self._refresh_periods)
        ctrl_row.addWidget(self.btn_refresh)

        self.btn_generate = QPushButton("📄 Generate Slip(s)")
        self.btn_generate.setObjectName("successButton")
        self.btn_generate.setFixedHeight(36)
        self.btn_generate.setMinimumWidth(150)
        self.btn_generate.setEnabled(False)
        self.btn_generate.clicked.connect(self._on_generate_slip)
        ctrl_row.addWidget(self.btn_generate)

        header_layout.addLayout(ctrl_row)
        layout.addWidget(header_card)

        # ── Stats row ────────────────────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self.stat_employees = self._make_stat_card("Employees", "0", "#4FC3F7")
        self.stat_gross = self._make_stat_card("Total Gross", "₹0", "#81C784")
        self.stat_net = self._make_stat_card("Total Net", "₹0", "#FFB74D")
        self.stat_deductions = self._make_stat_card("Total Deductions", "₹0", "#F06292")

        for card in [self.stat_employees, self.stat_gross, self.stat_net, self.stat_deductions]:
            stats_row.addWidget(card)

        layout.addLayout(stats_row)

        # ── Chart card ───────────────────────────────────────────────────────
        chart_card = QFrame()
        chart_card.setObjectName("card")
        chart_outer = QVBoxLayout(chart_card)
        chart_outer.setContentsMargins(20, 16, 20, 16)
        chart_outer.setSpacing(12)

        chart_title_row = QHBoxLayout()
        chart_title = QLabel("Monthly Salary Spend")
        chart_title.setObjectName("cardHeader")
        chart_title_row.addWidget(chart_title)
        chart_title_row.addStretch()
        self.lbl_chart_scope = QLabel("All Periods")
        self.lbl_chart_scope.setObjectName("badge")
        chart_title_row.addWidget(self.lbl_chart_scope)
        chart_outer.addLayout(chart_title_row)

        self.chart_view = QChartView()
        self.chart_view.setMinimumHeight(340)
        self.chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chart_view.setFrameShape(QFrame.NoFrame)
        chart_outer.addWidget(self.chart_view)

        layout.addWidget(chart_card)
        layout.addStretch()

    def _make_stat_card(self, label: str, value: str, accent: str) -> QFrame:
        """Create a small stat card with an accent top border."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(160)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setStyleSheet(f"QFrame#card {{ border-top: 3px solid {accent}; }}")

        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 11px;")
        v.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {accent};")
        v.addWidget(val)

        card._value_label = val
        return card

    # ─────────────────────────────────────────────────────────────────────────
    # DATA LOADING
    # ─────────────────────────────────────────────────────────────────────────

    def _load_periods(self):
        """Populate the period combo with periods that have data for this company."""
        self.period_combo.blockSignals(True)
        self.period_combo.clear()
        self.period_combo.addItem("-- Select Period --", None)

        db = get_db()
        with db.get_session() as session:
            period_repo = PayrollPeriodRepository(session)
            payroll_repo = MonthlyPayrollRepository(session)
            for period in period_repo.get_all_ordered():
                if payroll_repo.exists_for_period_and_company(period.id, self.selected_company_id):
                    self.period_combo.addItem(f"📝 {period.period_label}", period.id)

        self.period_combo.blockSignals(False)
        self._on_period_changed(0)

    def _refresh_periods(self):
        current = self.period_combo.currentData()
        self._load_periods()
        for i in range(self.period_combo.count()):
            if self.period_combo.itemData(i) == current:
                self.period_combo.setCurrentIndex(i)
                break
        self._refresh_chart()

    def _on_period_changed(self, _index: int = 0):
        period_id = self.period_combo.currentData()
        self._load_employees(period_id)
        self._update_stats(period_id)
        self.btn_generate.setEnabled(period_id is not None)

    def _load_employees(self, period_id):
        self.employee_combo.clear()
        self.employee_combo.addItem("-- All Employees --", None)
        if not period_id:
            return
        db = get_db()
        with db.get_session() as session:
            for p in MonthlyPayrollRepository(session).get_all_for_period_and_company(
                period_id, self.selected_company_id
            ):
                self.employee_combo.addItem(
                    f"{p.employee.employee_code} - {p.employee.full_name}",
                    p.employee.id,
                )

    def _update_stats(self, period_id):
        """Refresh the 4 stat cards for the given period."""
        if not period_id:
            self.stat_employees._value_label.setText("0")
            for card in [self.stat_gross, self.stat_net, self.stat_deductions]:
                card._value_label.setText("₹0")
            return

        db = get_db()
        with db.get_session() as session:
            payrolls = MonthlyPayrollRepository(session).get_all_for_period_and_company(
                period_id, self.selected_company_id
            )
            count = len(payrolls)
            total_gross = sum(float(p.gross_earnings) for p in payrolls)
            total_net = sum(float(p.net_salary) for p in payrolls)
            total_ded = sum(
                float(p.pf_employee or 0)
                + float(p.esi_employee or 0)
                + float(p.professional_tax or 0)
                + float(p.loan_deduction or 0)
                + float(p.tds or 0)
                for p in payrolls
            )

        self.stat_employees._value_label.setText(str(count))
        self.stat_gross._value_label.setText(f"₹{total_gross:,.0f}")
        self.stat_net._value_label.setText(f"₹{total_net:,.0f}")
        self.stat_deductions._value_label.setText(f"₹{total_ded:,.0f}")

    # ─────────────────────────────────────────────────────────────────────────
    # CHART
    # ─────────────────────────────────────────────────────────────────────────

    def _refresh_chart(self):
        """Build a line chart of monthly Net + Gross salary spend over all periods."""
        db = get_db()
        period_labels = []
        net_values = []
        gross_values = []

        with db.get_session() as session:
            period_repo = PayrollPeriodRepository(session)
            payroll_repo = MonthlyPayrollRepository(session)
            periods = period_repo.get_all_ordered()

            for period in periods:
                payrolls = payroll_repo.get_all_for_period_and_company(
                    period.id, self.selected_company_id
                )
                if not payrolls:
                    continue
                period_labels.append(period.period_label)
                net_values.append(sum(float(p.net_salary) for p in payrolls))
                gross_values.append(sum(float(p.gross_earnings) for p in payrolls))

        chart = QChart()
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundRoundness(0)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.setMargins(QMargins(0, 8, 32, 0))

        # Theme-aware styling — transparent bg so chart blends into card
        colors = get_theme().colors
        chart.setBackgroundBrush(QBrush(Qt.transparent))
        chart.setPlotAreaBackgroundBrush(QBrush(QColor(colors.background)))
        chart.setPlotAreaBackgroundVisible(True)
        chart.legend().setColor(QColor(colors.text_primary))
        chart.legend().setLabelColor(QColor(colors.text_primary))
        chart.setTitleBrush(QBrush(QColor(colors.text_primary)))

        if not period_labels:
            chart.setTitle("No data available yet")
            self.chart_view.setChart(chart)
            return

        # Series
        max_val = max(gross_values) if gross_values else 1
        # Scale Y to readable units: Lakhs (L) if >= 1L, else Thousands (K)
        if max_val >= 100_000:
            y_scale = 100_000
            y_fmt = "%.2f L"
        elif max_val >= 1_000:
            y_scale = 1_000
            y_fmt = "%.1f K"
        else:
            y_scale = 1
            y_fmt = "%.0f"

        net_series = QLineSeries()
        net_series.setName("Net Salary")
        pen_net = QPen(QColor("#FFB74D"))
        pen_net.setWidth(2)
        net_series.setPen(pen_net)

        gross_series = QLineSeries()
        gross_series.setName("Gross Salary")
        pen_gross = QPen(QColor("#81C784"))
        pen_gross.setWidth(2)
        gross_series.setPen(pen_gross)

        for i, (n, g) in enumerate(zip(net_values, gross_values)):
            net_series.append(i, n / y_scale)
            gross_series.append(i, g / y_scale)

        chart.addSeries(net_series)
        chart.addSeries(gross_series)

        # X axis — period name labels;
        axis_x = QCategoryAxis()
        axis_x.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        for i, label in enumerate(period_labels):
            axis_x.append(label, i)
        axis_x.setRange(0, max(len(period_labels) - 1, 1))
        axis_x.setLabelsAngle(-30)
        axis_x.setLabelsColor(QColor(colors.text_primary))
        axis_x.setGridLineColor(QColor(colors.border))
        axis_x.setLinePenColor(QColor(colors.border))

        # Y axis — scale to K or L so numbers read naturally
        axis_y = QValueAxis()
        axis_y.setRange(0, (max_val / y_scale) * 1.15)
        axis_y.setLabelFormat(y_fmt)
        axis_y.setTickCount(6)
        axis_y.setLabelsColor(QColor(colors.text_primary))
        axis_y.setGridLineColor(QColor(colors.border))
        axis_y.setLinePenColor(QColor(colors.border))

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        net_series.attachAxis(axis_x)
        net_series.attachAxis(axis_y)
        gross_series.attachAxis(axis_x)
        gross_series.attachAxis(axis_y)

        self.lbl_chart_scope.setText(f"{len(period_labels)} period(s)")
        self.chart_view.setChart(chart)

    # ─────────────────────────────────────────────────────────────────────────
    # SALARY SLIP GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    def _on_generate_slip(self):
        period_id = self.period_combo.currentData()
        employee_id = self.employee_combo.currentData()

        if not period_id:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", "", QFileDialog.ShowDirsOnly
        )
        if not output_dir:
            return

        try:
            db = get_db()
            with db.get_session() as session:
                payroll_repo = MonthlyPayrollRepository(session)

                if employee_id:
                    payroll = payroll_repo.get_by_employee_and_period(employee_id, period_id)
                    if not payroll:
                        QMessageBox.warning(self, "Not Found", "No payroll record found for this employee.")
                        return
                    payrolls = [payroll]
                else:
                    payrolls = payroll_repo.get_all_for_period_and_company(
                        period_id, self.selected_company_id
                    )

                if not payrolls:
                    QMessageBox.warning(self, "No Data", "No payroll records found.")
                    return

                progress = QProgressDialog(
                    "Generating salary slips...", "Cancel", 0, len(payrolls), self
                )
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)

                company_key = (self.selected_company_code or self.selected_company_name or "").upper()
                template_name = "HNL" if "HNL" in company_key else "Endee"
                generator = SalarySlipGenerator(template_name=template_name)

                from pathlib import Path
                leave_repo = LeaveBalanceRepository(session)
                fy = None
                if payrolls:
                    _fp = payrolls[0].payroll_period
                    fy = get_financial_year(_fp.year, _fp.month)

                generated = []
                for i, payroll in enumerate(payrolls):
                    if progress.wasCanceled():
                        break
                    progress.setValue(i)
                    progress.setLabelText(f"Generating for {payroll.employee.full_name}...")

                    period = payroll.payroll_period
                    emp_name = (
                        (payroll.employee.full_name or payroll.employee.employee_code)
                        .replace(" ", "_")
                        .replace("/", "-")
                    )
                    filename = f"Salary_Slip_{emp_name}_{period.period_label.replace(' ', '_')}.pdf"
                    output_path = Path(output_dir) / filename

                    leave_bal = leave_repo.get_for_employee_fy(payroll.employee_id, fy) if fy else None
                    generator.generate_slip(payroll, output_path, leave_balance=leave_bal)
                    generated.append(output_path)

                progress.setValue(len(payrolls))

            QMessageBox.information(
                self,
                "Success",
                f"Generated {len(generated)} salary slip(s) in:\n{output_dir}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate slips:\n{str(e)}")

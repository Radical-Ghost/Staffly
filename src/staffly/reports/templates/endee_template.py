"""Endee Engineers salary slip template using ReportLab."""

from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from staffly.database.models import MonthlyPayroll
from .base_template import BaseSlipTemplate, to_decimal, format_currency, number_to_words


class _Slot(NamedTuple):
    label: str
    amount: str


_EMPTY = _Slot("", "")


class EndeeTemplate(BaseSlipTemplate):
    """Salary slip template for ENDEE ENGINEERS PVT. LTD. using ReportLab."""

    name = "Endee"
    description = "ENDEE ENGINEERS PVT. LTD. template"

    HEADER_BLUE  = colors.Color(30/255,  45/255,  100/255)
    ED_COL_WIDTHS = [63 * mm, 27 * mm, 63 * mm, 27 * mm]
    ED_ROW_HEIGHTS = [8, 8, 8, 8, 8, 8, 8, 8, 8, 8]

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_logo_filename(self) -> str:
        return "Endee.jpeg"

    def _resolve_logo_path(self) -> Path | None:
        logo_name = self._get_logo_filename()
        candidates = [
            Path(__file__).resolve().parent / "assets" / logo_name,
            Path.cwd() / logo_name,
            Path(__file__).resolve().parents[4] / logo_name,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _register_fonts(self):
        try:
            pdfmetrics.registerFont(TTFont('Calibri',      'C:/Windows/Fonts/calibri.ttf'))
            pdfmetrics.registerFont(TTFont('Calibri-Bold', 'C:/Windows/Fonts/calibrib.ttf'))
            return 'Calibri', 'Calibri-Bold'
        except Exception:
            return 'Helvetica', 'Helvetica-Bold'

    # ── slot builders ─────────────────────────────────────────────────────────

    @staticmethod
    def _build_earn_bot(pf_er_d: Decimal, bonus_d: Decimal, arrears_d: Decimal) -> list[_Slot]:
        """
        Variable earning slots for rows 5-7.
        Priority order: PF Employer → Bonus → Arrears.
        Each item occupies the next available slot; unused slots are empty.
        """
        pending: list[_Slot] = []
        if pf_er_d > 0:
            pending.append(_Slot("PF (Employer-contribution)", format_currency(pf_er_d)))
        if bonus_d > 0:
            pending.append(_Slot("Bonus", format_currency(bonus_d)))
        if arrears_d > 0:
            pending.append(_Slot("Arrears", format_currency(arrears_d)))
        while len(pending) < 3:
            pending.append(_EMPTY)
        return pending[:3]

    @staticmethod
    def _build_ded_top(pf_emp_d: Decimal, esi_emp_d: Decimal, pt_d: Decimal) -> list[_Slot]:
        """
        Fixed deduction slots for rows 0-2 (cascading fill).
        Row 0: PF(Emp) → ESIC → Prof Tax
        Row 1: ESIC (if not yet shown) → Prof Tax (if not yet shown) → blank
        Row 2: Prof Tax (if not yet shown) → blank
        """
        slots: list[_Slot] = []
        shown: set[str] = set()

        # Row 0
        if pf_emp_d > 0:
            slots.append(_Slot("PF (Employee)", format_currency(pf_emp_d)))
            shown.add("pf")
        elif esi_emp_d > 0:
            slots.append(_Slot("ESIC (Employee)", format_currency(esi_emp_d)))
            shown.add("esi")
        elif pt_d > 0:
            slots.append(_Slot("Professional Tax", format_currency(pt_d)))
            shown.add("pt")
        else:
            slots.append(_EMPTY)

        # Row 1
        if "esi" not in shown and esi_emp_d > 0:
            slots.append(_Slot("ESIC (Employee)", format_currency(esi_emp_d)))
            shown.add("esi")
        elif "pt" not in shown and pt_d > 0:
            slots.append(_Slot("Professional Tax", format_currency(pt_d)))
            shown.add("pt")
        else:
            slots.append(_EMPTY)

        # Row 2
        if "pt" not in shown and pt_d > 0:
            slots.append(_Slot("Professional Tax", format_currency(pt_d)))
        else:
            slots.append(_EMPTY)

        return slots

    @staticmethod
    def _build_ded_bot(pf_er_d: Decimal, loan_d: Decimal, tds_d: Decimal) -> list[_Slot]:
        """
        Variable deduction slots for rows 5-7 (cascading fill).
        Row 5: PF(Employer) → Advance/Loan → TDS
        Row 6: Advance/Loan (if not yet shown) → TDS (if not yet shown) → blank
        Row 7: TDS (if not yet shown) → blank
        """
        slots: list[_Slot] = []
        shown: set[str] = set()

        # Row 5
        if pf_er_d > 0:
            slots.append(_Slot("PF (Employer-contribution)", format_currency(pf_er_d)))
            shown.add("pf_er")
        elif loan_d > 0:
            slots.append(_Slot("Advance/Loan", format_currency(loan_d)))
            shown.add("loan")
        elif tds_d > 0:
            slots.append(_Slot("TDS", format_currency(tds_d)))
            shown.add("tds")
        else:
            slots.append(_EMPTY)

        # Row 6
        if "loan" not in shown and loan_d > 0:
            slots.append(_Slot("Advance/Loan", format_currency(loan_d)))
            shown.add("loan")
        elif "tds" not in shown and tds_d > 0:
            slots.append(_Slot("TDS", format_currency(tds_d)))
            shown.add("tds")
        else:
            slots.append(_EMPTY)

        # Row 7
        if "tds" not in shown and tds_d > 0:
            slots.append(_Slot("TDS", format_currency(tds_d)))
        else:
            slots.append(_EMPTY)

        return slots

    # ── main generate ─────────────────────────────────────────────────────────

    def generate(
        self,
        payroll: MonthlyPayroll,
        output_path: Path,
        company_name: str,
        company_address: str,
        leave_balance=None,
    ) -> Path:
        """Generate the Endee format salary slip using ReportLab."""
        width, height = A4
        margin = 15 * mm
        content_width = width - 2 * margin

        font_regular, font_bold = self._register_fonts()
        c = canvas.Canvas(str(output_path), pagesize=A4)

        employee = payroll.employee
        period   = payroll.payroll_period

        border_padding = 5 * mm
        y_start = height - 12 * mm
        y = y_start

        # ── HEADER ────────────────────────────────────────────────────────────
        c.setFillColor(self.HEADER_BLUE)
        c.setFont(font_bold, 13)
        c.drawCentredString(width / 2, y, company_name)
        y -= 4 * mm

        c.setFillColor(colors.black)
        c.setFont(font_regular, 7)
        c.drawCentredString(width / 2, y, company_address)
        y -= 5 * mm

        c.setFont(font_bold, 9)
        c.drawCentredString(width / 2, y, "Monthly Salary Slip")
        y -= 2 * mm

        header_line_y = y
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.line(margin, header_line_y, width - margin, header_line_y)

        logo_path = self._resolve_logo_path()
        if logo_path is not None:
            try:
                image = ImageReader(str(logo_path))
                img_w, img_h = image.getSize()
                if img_w and img_h:
                    logo_height = y_start - header_line_y + 3 * mm
                    logo_width  = logo_height * (img_w / img_h)
                    c.drawImage(
                        str(logo_path),
                        margin - 0.1 * mm,
                        header_line_y + 1 * mm,
                        width=logo_width,
                        height=logo_height,
                        mask='auto',
                    )
            except Exception:
                pass

        y -= 1 * mm

        # ── EMPLOYEE INFO ─────────────────────────────────────────────────────
        month_str    = f"{self._get_month_name(period.month)}-{period.year}"
        joining_date = employee.date_of_joining.strftime("%d - %m - %Y") if employee.date_of_joining else "-"

        wrap_style = ParagraphStyle(
            'wrap',
            fontName=font_regular,
            fontSize=7,
            leading=7,
            spaceBefore=0, spaceAfter=0,
        )
        wrap_bold = ParagraphStyle(
            'wrap_bold',
            fontName=font_bold,
            fontSize=7,
            leading=7,
            spaceBefore=0, spaceAfter=0,
        )

        col_widths = [24*mm, 48*mm, 18*mm, 30*mm, 18*mm, 10*mm, 18*mm, 10*mm]

        pl_adj = f"{float(payroll.privilege_leave or 0):.1f}"
        sl_adj = f"{float(payroll.sick_leave     or 0):.1f}"
        cl_adj = f"{float(payroll.casual_leave   or 0):.1f}"
        if leave_balance is not None:
            pl_bal = f"{float(leave_balance.pl_balance):.1f}"
            sl_bal = f"{float(leave_balance.sl_balance):.1f}"
            cl_bal = f"{float(leave_balance.cl_balance):.1f}"
        else:
            pl_bal = f"{7.0 - float(payroll.privilege_leave or 0):.1f}"
            sl_bal = f"{7.0 - float(payroll.sick_leave     or 0):.1f}"
            cl_bal = f"{7.0 - float(payroll.casual_leave   or 0):.1f}"

        def P(text, bold=False) -> Paragraph:
            return Paragraph(text, wrap_bold if bold else wrap_style)

        info_data = [
            [P("Employee Code:"), P(employee.employee_code or "-"),
             P("Month:"),         P(month_str, bold=True),
             P("Present Days:"),  P(str(payroll.present_days or 0)),
             P("<u>Leaves Record:</u>"), ""],

            [P("Name of Employee:"), P(employee.full_name or "-"),
             P("Paid Days:"),        P(str(payroll.paid_days or 0)),
             P("PL Adjusted:"),      P(pl_adj),
             P("PL Balance:"),       P(pl_bal)],

            [P("Designation:"), P(employee.designation or "-"),
             P("PF (UAN) No.:"), P(employee.uan_number or "NA"),
             P("SL Adjusted:"),  P(sl_adj),
             P("SL Balance:"),   P(sl_bal)],

            [P("Department:"), P(employee.department or "-"),
             P("ESIC No.:"),   P(employee.esi_number or "NA"),
             P("CL Adjusted:"), P(cl_adj),
             P("CL Balance:"),  P(cl_bal)],

            [P("Branch/ Factory:"), P(employee.branch or "-"),
             "", "",
             P("Absent Days:"), P(str(payroll.absent_days or 0)),
             "", ""],

            [P("Date of Joining:"), P(joining_date),
             "", "",
             P("Late Marks:"), P(str(payroll.late_marks or 0)),
             "", ""],
        ]

        info_table = Table(info_data, colWidths=col_widths, rowHeights=[8] * 6)
        info_table.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('ALIGN',         (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN',         (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN',         (4, 0), (4, -1), 'RIGHT'),
            ('ALIGN',         (6, 0), (6, -1), 'RIGHT'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0.25 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.25 * mm),
        ]))

        tw, th = info_table.wrap(content_width, y)
        info_table.drawOn(c, margin, y - th)
        y = y - th - 2.5 * mm

        # ── EARNINGS / DEDUCTIONS HEADER ──────────────────────────────────────
        header_table = Table(
            [["Earnings", "Amount", "Deductions", "Amount"]],
            colWidths=self.ED_COL_WIDTHS,
        )
        header_table.setStyle(TableStyle([
            ('FONTNAME',      (0, 0), (-1, -1), font_bold),
            ('FONTSIZE',      (0, 0), (-1, -1), 7),
            ('TEXTCOLOR',     (0, 0), (-1, -1), self.HEADER_BLUE),
            ('ALIGN',         (1, 0), (1, 0),   'RIGHT'),
            ('ALIGN',         (3, 0), (3, 0),   'RIGHT'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            ('LINEABOVE',     (0, 0), (-1, 0),  0.5, colors.black),
            ('LINEBELOW',     (0, 0), (-1, 0),  0.5, colors.black),
        ]))

        hw, hh = header_table.wrap(content_width, y)
        header_table.drawOn(c, margin, y - hh)
        y = y - hh - 1 * mm

        # ── SLOT DATA ─────────────────────────────────────────────────────────
        pf_emp_d  = to_decimal(payroll.pf_employee)
        pf_er_d   = to_decimal(payroll.pf_employer)
        esi_emp_d = to_decimal(payroll.esi_employee)
        pt_d      = to_decimal(payroll.professional_tax)
        loan_d    = to_decimal(payroll.loan_deduction)
        tds_d     = to_decimal(payroll.tds)
        bonus_d   = to_decimal(payroll.bonus)
        arrears_d = to_decimal(getattr(payroll, 'arrears', None) or 0)

        def _fc(val) -> str:
            v = to_decimal(val)
            return format_currency(v) if v > 0 else ""

        earn_bot = self._build_earn_bot(pf_er_d, bonus_d, arrears_d)
        ded_top  = self._build_ded_top(pf_emp_d, esi_emp_d, pt_d)
        ded_bot  = self._build_ded_bot(pf_er_d, loan_d, tds_d)

        # ── BUILD ROWS ────────────────────────────────────────────────────────
        # Indices 0-3: fixed rows
        # Index  4:    blank separator (3 pt tall) – LINEABOVE on index 5 shows the divider
        # Indices 5-7: variable rows
        # Indices 8-9: trailing blank spacing rows
        SEP = 4  # separator row index
        VAR_START = 5
        VAR_END = 7

        ed_rows = [
            # Row 0
            ["Basic Salary",               _fc(payroll.basic_salary),  ded_top[0].label, ded_top[0].amount],
            # Row 1
            ["House Rent Allowance (HRA)", _fc(payroll.hra),           ded_top[1].label, ded_top[1].amount],
            # Row 2
            ["CCA Allowance",              _fc(payroll.cca),           ded_top[2].label, ded_top[2].amount],
            # Row 3
            ["Other Allowance",            _fc(payroll.other_allowance), "",              ""],
            # Row 4 – blank gap
            ["", "", "", ""],
            # Rows 5-7 – variable
            [earn_bot[0].label, earn_bot[0].amount, ded_bot[0].label, ded_bot[0].amount],
            [earn_bot[1].label, earn_bot[1].amount, ded_bot[1].label, ded_bot[1].amount],
            [earn_bot[2].label, earn_bot[2].amount, ded_bot[2].label, ded_bot[2].amount],
            # Rows 8-9 – blank spacing
            ["", "", "", ""],
            ["", "", "", ""],
        ]

        data_table = Table(ed_rows, colWidths=self.ED_COL_WIDTHS, rowHeights=self.ED_ROW_HEIGHTS)
        data_table.setStyle(TableStyle([
            ('FONTNAME',      (0, 0), (-1, -1), font_regular),
            ('FONTSIZE',      (0, 0), (-1, -1), 7),
            ('ALIGN',         (1, 0), (1, -1),  'RIGHT'),
            ('ALIGN',         (3, 0), (3, -1),  'RIGHT'),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            # Separator: top outline of the first variable row (= bottom of gap row)
            ('LINEABOVE', (0, SEP + 1), (-1, SEP + 1), 0.5, colors.black),
            # Outline of the variable 3-row block
            ('LINEBELOW', (0, VAR_END), (-1, VAR_END), 0.5, colors.black),
        ]))

        dw, dh = data_table.wrap(content_width, y)
        data_table.drawOn(c, margin, y - dh)
        y = y - dh - 1 * mm

        # ── TOTALS ROW ────────────────────────────────────────────────────────
        gross            = to_decimal(payroll.gross_earnings) + arrears_d
        deductions_total = to_decimal(payroll.total_deductions)
        net              = to_decimal(payroll.net_salary) + arrears_d

        totals_table = Table(
            [["Total Earnings:", format_currency(gross),
              "Total Deductions:", format_currency(deductions_total)]],
            colWidths=self.ED_COL_WIDTHS,
        )
        totals_table.setStyle(TableStyle([
            ('FONTNAME',      (0, 0), (-1, -1), font_bold),
            ('FONTSIZE',      (0, 0), (-1, -1), 7),
            ('ALIGN',         (1, 0), (1, 0),   'RIGHT'),
            ('ALIGN',         (3, 0), (3, 0),   'RIGHT'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            ('LINEABOVE',     (0, 0), (-1, 0),  0.5, colors.black),
            ('LINEBELOW',     (0, 0), (-1, 0),  0.5, colors.black),
        ]))

        tw2, th2 = totals_table.wrap(content_width, y)
        totals_table.drawOn(c, margin, y - th2)
        y = y - th2

        # ── NET PAYABLE ROW ───────────────────────────────────────────────────
        net_words = number_to_words(float(net))
        net_table = Table(
            [[net_words, "Net Payable:", format_currency(net)]],
            colWidths=[90*mm, 50*mm, 40*mm],
        )
        net_table.setStyle(TableStyle([
            ('FONTNAME',      (0, 0), (-1, -1), font_bold),
            ('FONTSIZE',      (0, 0), (0, 0),   7),
            ('FONTSIZE',      (1, 0), (2, 0),   8),
            ('ALIGN',         (2, 0), (2, 0),   'RIGHT'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            ('LINEABOVE',     (0, 0), (-1, 0),  0.5, colors.black),
            ('LINEBELOW',     (0, 0), (-1, 0),  0.5, colors.black),
        ]))

        nw, nh = net_table.wrap(content_width, y)
        net_table.drawOn(c, margin, y - nh)
        y = y - nh - 2 * mm

        # ── FOOTER ────────────────────────────────────────────────────────────
        c.setFillColor(self.HEADER_BLUE)
        c.setFont(font_regular, 7)
        c.drawString(margin, y, "This is computer generated memo and requires no signature")
        y -= 2 * mm

        # ── OUTER BORDER ──────────────────────────────────────────────────────
        c.setStrokeColor(self.HEADER_BLUE)
        c.setLineWidth(1.5)
        c.rect(
            margin - border_padding,
            y,
            content_width + 2 * border_padding,
            y_start - y + border_padding,
            stroke=1, fill=0,
        )

        c.save()
        return output_path

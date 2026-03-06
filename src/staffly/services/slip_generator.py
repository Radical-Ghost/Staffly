"""Salary slip PDF generator."""

from decimal import Decimal
from pathlib import Path
from typing import Optional
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from staffly.database.models import MonthlyPayroll, Employee
from staffly.config import get_config


def _to_decimal(value) -> Decimal:
    """Convert value to Decimal, treating None as 0."""
    if value is None:
        return Decimal("0.00")
    return value


def _format_currency(amount: Decimal) -> str:
    """Format amount as currency string."""
    return f"{float(amount):,.2f}"


def _number_to_words(num: float) -> str:
    """Convert number to words (Indian numbering system)."""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    
    def words(n):
        if n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
        elif n < 1000:
            return ones[n // 100] + ' Hundred' + (' ' + words(n % 100) if n % 100 else '')
        elif n < 100000:
            return words(n // 1000) + ' Thousand' + (' ' + words(n % 1000) if n % 1000 else '')
        elif n < 10000000:
            return words(n // 100000) + ' Lakh' + (' ' + words(n % 100000) if n % 100000 else '')
        else:
            return words(n // 10000000) + ' Crore' + (' ' + words(n % 10000000) if n % 10000000 else '')
    
    num = int(round(num))
    if num == 0:
        return 'Zero'
    
    result = words(num)
    return f"Rupees {result} Only"


class SalarySlipGenerator:
    """
    Generates salary slip PDFs.
    
    Based on the ENDEE ENGINEERS template format.
    """
    
    def __init__(self):
        self.config = get_config()
        self.page_width, self.page_height = A4
        self.margin = 15 * mm
        
    def generate_slip(
        self,
        payroll: MonthlyPayroll,
        output_path: Path,
        company_name: str = None,
        company_address: str = None,
    ) -> Path:
        """
        Generate a salary slip PDF for a single employee.
        
        Args:
            payroll: The MonthlyPayroll record
            output_path: Where to save the PDF
            company_name: Company name (uses config default if not provided)
            company_address: Company address (uses config default if not provided)
            
        Returns:
            Path to the generated PDF
        """
        company_name = company_name or self.config.company_name
        company_address = company_address or self.config.company_address
        
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )
        
        elements = []
        
        # Build the slip content
        elements.extend(self._build_header(company_name, company_address))
        elements.append(Spacer(1, 5 * mm))
        elements.extend(self._build_employee_info(payroll))
        elements.append(Spacer(1, 5 * mm))
        elements.extend(self._build_earnings_deductions(payroll))
        elements.append(Spacer(1, 5 * mm))
        elements.extend(self._build_totals(payroll))
        elements.append(Spacer(1, 8 * mm))
        elements.extend(self._build_footer())
        
        doc.build(elements)
        return output_path
    
    def _build_header(self, company_name: str, company_address: str) -> list:
        """Build the header section."""
        styles = getSampleStyleSheet()
        
        # Company name style
        company_style = ParagraphStyle(
            'CompanyName',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=2 * mm,
            textColor=colors.HexColor('#1a237e'),
        )
        
        # Address style
        address_style = ParagraphStyle(
            'Address',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#333333'),
        )
        
        # Title style
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading2'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        )
        
        elements = [
            Paragraph(company_name, company_style),
            Paragraph(company_address, address_style),
            Paragraph("Monthly Salary Slip", title_style),
        ]
        
        return elements
    
    def _build_employee_info(self, payroll: MonthlyPayroll) -> list:
        """Build the employee information section."""
        employee = payroll.employee
        period = payroll.payroll_period
        
        # Format month
        month_names = ["", "January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        month_str = f"{month_names[period.month]}-{period.year}"
        
        # Employee info data - 4 columns layout
        data = [
            ["Employee Code:", employee.employee_code, "Month:", month_str,
             "Present Days:", str(payroll.present_days or 0), "Leaves Record:", ""],
            ["Name of Employee:", employee.full_name, "Paid Days:", str(payroll.paid_days or 0),
             "PL Adjusted:", "0", "PL Balance:", "0"],
            ["Designation:", employee.designation or "-", "PF (UAN) No.:", employee.uan_number or "NA",
             "SL Adjusted:", "0", "SL Balance:", "0"],
            ["Department:", employee.department or "-", "ESIC No.:", employee.esi_number or "NA",
             "CL Adjusted:", "0", "CL Balance:", "0"],
            ["Branch/Factory:", "-", "", "",
             "Absent Days:", str(payroll.absent_days or 0), "", ""],
            ["Date of Joining:", employee.date_of_joining.strftime("%d-%m-%Y") if employee.date_of_joining else "-",
             "", "", "Late Marks:", str(payroll.late_marks or 0), "", ""],
        ]
        
        # Create table
        col_widths = [75, 110, 65, 80, 60, 30, 55, 30]
        table = Table(data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            # Header row styling
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Labels bold
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (4, 0), (4, -1), 'Helvetica-Bold'),
            ('FONTNAME', (6, 0), (6, -1), 'Helvetica-Bold'),
            # Grid
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            # Background
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ]))
        
        return [table]
    
    def _build_earnings_deductions(self, payroll: MonthlyPayroll) -> list:
        """Build the earnings and deductions section."""
        # Earnings data
        basic = _to_decimal(payroll.basic_salary)
        hra = _to_decimal(payroll.hra)
        bonus = _to_decimal(payroll.bonus)
        cca = _to_decimal(payroll.cca)
        other = _to_decimal(payroll.other_allowance)
        
        # Deductions data
        pf_employee = _to_decimal(payroll.pf_employee)
        esi_employee = _to_decimal(payroll.esi_employee)
        professional_tax = _to_decimal(payroll.professional_tax)
        tds = _to_decimal(payroll.tds)
        loan = _to_decimal(payroll.loan_deduction)
        other_ded = _to_decimal(payroll.other_deductions)
        
        # Header
        header = [["Earnings", "", "Amount", "Deductions", "", "Amount"]]
        
        # Earnings and deductions rows
        earnings = [
            ("Basic Salary", basic),
            ("House Rent Allowance (HRA)", hra),
            ("Bonus", bonus),
            ("CCA Allowance", cca),
            ("Other Allowance", other),
        ]
        
        deductions = [
            ("Provident Fund (PF)", pf_employee),
            ("ESI", esi_employee),
            ("Professional Tax", professional_tax),
            ("TDS", tds),
            ("Loan Deduction", loan),
            ("Other Deductions", other_ded),
        ]
        
        # Build rows
        data = header.copy()
        max_rows = max(len(earnings), len(deductions))
        
        for i in range(max_rows):
            row = []
            
            # Earnings
            if i < len(earnings):
                name, amount = earnings[i]
                if amount > 0:
                    row.extend([name, "", _format_currency(amount)])
                else:
                    row.extend(["", "", ""])
            else:
                row.extend(["", "", ""])
            
            # Deductions
            if i < len(deductions):
                name, amount = deductions[i]
                if amount > 0:
                    row.extend([name, "", _format_currency(amount)])
                else:
                    row.extend(["", "", ""])
            else:
                row.extend(["", "", ""])
            
            data.append(row)
        
        # Create table
        col_widths = [130, 10, 80, 130, 10, 80]
        table = Table(data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            # Header background
            ('BACKGROUND', (0, 0), (2, 0), colors.HexColor('#c8e6c9')),
            ('BACKGROUND', (3, 0), (5, 0), colors.HexColor('#ffcdd2')),
            # Grid
            ('BOX', (0, 0), (2, -1), 0.5, colors.black),
            ('BOX', (3, 0), (5, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (2, 0), 1, colors.black),
            ('LINEBELOW', (3, 0), (5, 0), 1, colors.black),
        ]))
        
        return [table]
    
    def _build_totals(self, payroll: MonthlyPayroll) -> list:
        """Build the totals section."""
        gross = _to_decimal(payroll.gross_earnings)
        deductions = _to_decimal(payroll.total_deductions)
        net = _to_decimal(payroll.net_salary)
        
        # Amount in words
        net_in_words = _number_to_words(float(net))
        
        data = [
            ["Total Earnings:", "", _format_currency(gross), 
             "Total Deductions:", "", _format_currency(deductions)],
            [net_in_words, "", "", "Net Payable:", "", _format_currency(net)],
        ]
        
        col_widths = [130, 10, 80, 130, 10, 80]
        table = Table(data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            # Backgrounds
            ('BACKGROUND', (0, 0), (2, 0), colors.HexColor('#c8e6c9')),
            ('BACKGROUND', (3, 0), (5, 0), colors.HexColor('#ffcdd2')),
            ('BACKGROUND', (0, 1), (2, 1), colors.HexColor('#fff9c4')),
            ('BACKGROUND', (3, 1), (5, 1), colors.HexColor('#bbdefb')),
            # Grid
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Span amount in words
            ('SPAN', (0, 1), (2, 1)),
            ('FONTSIZE', (0, 1), (2, 1), 8),
        ]))
        
        return [table]
    
    def _build_footer(self) -> list:
        """Build the footer section."""
        styles = getSampleStyleSheet()
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666'),
            fontName='Helvetica-Oblique',
        )
        
        return [
            Paragraph("This is computer generated memo and requires no signature", footer_style)
        ]
    
    def generate_batch(
        self,
        payrolls: list,
        output_dir: Path,
        company_name: str = None,
        company_address: str = None,
    ) -> list:
        """
        Generate salary slips for multiple employees.
        
        Args:
            payrolls: List of MonthlyPayroll records
            output_dir: Directory to save PDFs
            company_name: Company name
            company_address: Company address
            
        Returns:
            List of paths to generated PDFs
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated = []
        for payroll in payrolls:
            period = payroll.payroll_period
            employee = payroll.employee
            
            filename = f"Salary_Slip_{employee.employee_code}_{period.period_label.replace(' ', '_')}.pdf"
            output_path = output_dir / filename
            
            self.generate_slip(payroll, output_path, company_name, company_address)
            generated.append(output_path)
        
        return generated

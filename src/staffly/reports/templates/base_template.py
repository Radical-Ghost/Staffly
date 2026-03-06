"""Base template class for salary slips using ReportLab."""

from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from staffly.database.models import MonthlyPayroll


def to_decimal(value) -> Decimal:
    """Convert value to Decimal, treating None as 0."""
    if value is None:
        return Decimal("0.00")
    return value


def format_currency(amount: Decimal) -> str:
    """Format amount as currency string."""
    return f"{float(amount):,.2f}"


def number_to_words(num: float) -> str:
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


class BaseSlipTemplate(ABC):
    """
    Abstract base class for salary slip templates using ReportLab.
    
    Subclass this to create custom templates.
    """
    
    # Template info
    name: str = "Base Template"
    description: str = "Base template for salary slips"
    
    def __init__(self):
        self.width, self.height = A4
        self.margin = 15 * mm
    
    @abstractmethod
    def generate(
        self,
        payroll: MonthlyPayroll,
        output_path: Path,
        company_name: str,
        company_address: str,
    ) -> Path:
        """
        Generate the salary slip PDF.
        
        Args:
            payroll: The MonthlyPayroll record
            output_path: Where to save the PDF
            company_name: Company name
            company_address: Company address
            
        Returns:
            Path to the generated PDF
        """
        pass
    
    def _get_month_name(self, month: int) -> str:
        """Get month name from month number."""
        months = ["", "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        return months[month] if 1 <= month <= 12 else ""
    
    def _create_canvas(self, output_path: Path) -> canvas.Canvas:
        """Create a new ReportLab canvas."""
        return canvas.Canvas(str(output_path), pagesize=A4)

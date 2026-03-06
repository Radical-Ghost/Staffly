"""Salary slip generator using templates."""

from pathlib import Path
from typing import List, Optional

from staffly.database.models import MonthlyPayroll
from staffly.config import get_config
from .templates import TEMPLATES, BaseSlipTemplate


class SalarySlipGenerator:
    """
    Generates salary slip PDFs using templates.
    
    Supports multiple templates (Endee, HNL, etc.)
    """
    
    def __init__(self, template_name: str = "Endee"):
        """
        Initialize generator with a template.
        
        Args:
            template_name: Name of template to use ("Endee" or "HNL")
        """
        self.config = get_config()
        self.set_template(template_name)
    
    @staticmethod
    def get_available_templates() -> List[str]:
        """Get list of available template names."""
        return list(TEMPLATES.keys())
    
    def set_template(self, template_name: str) -> None:
        """Set the template to use."""
        if template_name not in TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}. Available: {list(TEMPLATES.keys())}")
        self.template: BaseSlipTemplate = TEMPLATES[template_name]()
        self.template_name = template_name
    
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
        
        return self.template.generate(
            payroll=payroll,
            output_path=Path(output_path),
            company_name=company_name,
            company_address=company_address,
        )
    
    def generate_batch(
        self,
        payrolls: List[MonthlyPayroll],
        output_dir: Path,
        company_name: str = None,
        company_address: str = None,
    ) -> List[Path]:
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

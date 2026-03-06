"""Employee repository for database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import date

from staffly.database.models.employee import Employee
from .base_repository import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    """Repository for Employee operations."""

    def __init__(self, session: Session):
        super().__init__(session, Employee)

    def get_by_code(self, employee_code: str) -> Optional[Employee]:
        """Get employee by employee code."""
        return self.session.query(Employee).filter(
            Employee.employee_code == employee_code
        ).first()

    def get_all_active(self) -> List[Employee]:
        """Get all active employees."""
        return self.session.query(Employee).filter(
            Employee.is_active == True
        ).all()

    def get_by_company(self, company_id: int) -> List[Employee]:
        """Get all employees for a specific company."""
        return self.session.query(Employee).filter(
            Employee.company_id == company_id
        ).all()

    def get_active_by_company(self, company_id: int) -> List[Employee]:
        """Get all active employees for a specific company."""
        return self.session.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_active == True
        ).all()

    def get_active_on_date(self, check_date: date) -> List[Employee]:
        """
        Get employees who were active on a specific date.
        
        Active means:
        - is_active = True
        - date_of_joining <= check_date
        - date_of_leaving is NULL OR date_of_leaving >= check_date
        """
        return self.session.query(Employee).filter(
            Employee.is_active == True,
            Employee.date_of_joining <= check_date,
            (Employee.date_of_leaving.is_(None)) | (Employee.date_of_leaving >= check_date)
        ).all()

    def get_active_on_date_by_company(self, check_date: date, company_id: int) -> List[Employee]:
        """Get employees who were active on a specific date for a company."""
        return self.session.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.date_of_joining <= check_date,
            (Employee.date_of_leaving.is_(None)) | (Employee.date_of_leaving >= check_date)
        ).all()

    def search_by_name(self, name: str) -> List[Employee]:
        """Search employees by name (partial match)."""
        search_pattern = f"%{name}%"
        return self.session.query(Employee).filter(
            (Employee.first_name.ilike(search_pattern)) |
            (Employee.last_name.ilike(search_pattern))
        ).all()

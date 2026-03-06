"""Salary Structure repository for database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import date

from staffly.database.models.salary_structure import SalaryStructure
from .base_repository import BaseRepository


class SalaryStructureRepository(BaseRepository[SalaryStructure]):
    """Repository for SalaryStructure operations."""

    def __init__(self, session: Session):
        super().__init__(session, SalaryStructure)

    def get_by_employee_id(self, employee_id: int) -> List[SalaryStructure]:
        """Get all salary structures for an employee (ordered by effective_from desc)."""
        return self.session.query(SalaryStructure).filter(
            SalaryStructure.employee_id == employee_id
        ).order_by(SalaryStructure.effective_from.desc()).all()

    def get_active_for_employee(self, employee_id: int, on_date: date) -> Optional[SalaryStructure]:
        """
        Get the active salary structure for an employee on a specific date.
        
        Returns the structure where:
        - effective_from <= on_date
        - effective_to is NULL OR effective_to >= on_date
        """
        return self.session.query(SalaryStructure).filter(
            SalaryStructure.employee_id == employee_id,
            SalaryStructure.effective_from <= on_date,
            (SalaryStructure.effective_to.is_(None)) | (SalaryStructure.effective_to >= on_date)
        ).order_by(SalaryStructure.effective_from.desc()).first()

    def get_current_for_employee(self, employee_id: int) -> Optional[SalaryStructure]:
        """Get the current active salary structure for an employee."""
        return self.get_active_for_employee(employee_id, date.today())

    def close_current_structure(self, employee_id: int, end_date: date) -> None:
        """
        Close the current salary structure by setting effective_to date.
        Used when creating a new structure for appraisal/promotion.
        """
        current = self.get_current_for_employee(employee_id)
        if current and current.effective_to is None:
            current.effective_to = end_date
            self.session.flush()

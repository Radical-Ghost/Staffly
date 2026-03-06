"""Salary Structure model - stores employee salary definitions."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Numeric, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .employee import Employee


class SalaryStructure(BaseModel):
    """
    Salary Structure table.
    
    Stores the employee's salary breakup that is valid for a period of time.
    This is the contractual/entitlement data, NOT monthly calculations.
    
    Salary changes only when:
    - Appraisal happens
    - Role/designation change
    - Policy change
    
    NOT every month.
    """

    __tablename__ = "salary_structures"

    # Foreign Key to Employee
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Validity Period
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # EARNINGS COMPONENTS (Monthly contractual amounts)
    # ═══════════════════════════════════════════════════════════════════════════

    # Basic Salary - Foundation for PF/Gratuity calculations
    basic_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # House Rent Allowance (HRA) - Tax exemption available
    hra: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Bonus - Can be fixed monthly or as per policy
    bonus: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # City Compensatory Allowance (CCA) - For metro cities
    cca: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Other Allowance - Catch-all for additional components
    other_allowance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Provident Fund - Employer contribution (stored with structure calculation)
    pf_employer: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # STATUTORY APPLICABILITY FLAGS
    # ═══════════════════════════════════════════════════════════════════════════

    # Provident Fund (PF) - Applicable if salary <= threshold or by choice
    pf_applicable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Employee State Insurance (ESI) - Applicable if gross <= threshold
    esi_applicable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Professional Tax - State-specific
    pt_applicable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ═══════════════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════════════

    # Optional notes about this structure (e.g., "Post appraisal 2025")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship back to Employee
    employee: Mapped["Employee"] = relationship("Employee", back_populates="salary_structures")

    @property
    def gross_salary(self) -> Decimal:
        """Calculate the total gross salary from all components."""
        return (
            self.basic_salary
            + self.hra
            + self.bonus
            + self.cca
            + self.other_allowance
            + self.pf_employer
        )

    def is_active_on(self, check_date: date) -> bool:
        """Check if this salary structure is active on a given date."""
        if check_date < self.effective_from:
            return False
        if self.effective_to is not None and check_date > self.effective_to:
            return False
        return True

    def __repr__(self) -> str:
        return (
            f"<SalaryStructure(id={self.id}, employee_id={self.employee_id}, "
            f"basic={self.basic_salary}, effective_from={self.effective_from})>"
        )

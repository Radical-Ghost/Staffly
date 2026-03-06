"""Employee model - stores employee master data."""

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, String, Boolean, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import BaseModel

if TYPE_CHECKING:
    from .company import Company
    from .salary_structure import SalaryStructure
    from .monthly_payroll import MonthlyPayroll


class Gender(enum.Enum):
    """Gender enumeration."""
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class Employee(BaseModel):
    """
    Employee master table.
    
    Stores core employee information that doesn't change frequently.
    Salary details are stored separately in SalaryStructure.
    """

    __tablename__ = "employees"

    # Foreign Key to Company
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Unique identifier for the employee (e.g., EMP001)
    employee_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )

    # Personal Information
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # Male, Female, Other
    
    # Contact Information
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Employment Details
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    date_of_leaving: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Office/Branch location

    # Statutory IDs
    aadhar_number: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    pan_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    uan_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Universal Account Number (PF)
    esi_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # ESI Number

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="employees")
    salary_structures: Mapped[list["SalaryStructure"]] = relationship(
        "SalaryStructure",
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="SalaryStructure.effective_from.desc()",
    )
    monthly_payrolls: Mapped[list["MonthlyPayroll"]] = relationship(
        "MonthlyPayroll",
        back_populates="employee",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        """Return the full name of the employee."""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, code={self.employee_code}, name={self.full_name})>"

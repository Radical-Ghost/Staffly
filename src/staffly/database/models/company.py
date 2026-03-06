"""Company model - stores company information."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .employee import Employee


class Company(BaseModel):
    """
    Company table.
    
    Stores company information for multi-company support.
    Currently supports: Endee and HNL
    """

    __tablename__ = "companies"

    # Company name (e.g., "ENDEE ENGINEERS PVT. LTD.", "HNL")
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    
    # Short code for display (e.g., "Endee", "HNL")
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    
    # Company address
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Is this company active?
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationship to employees
    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="company")

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, code={self.code}, name={self.name})>"

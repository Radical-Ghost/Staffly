"""Company repository for database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session

from staffly.database.models.company import Company
from .base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Repository for Company operations."""

    def __init__(self, session: Session):
        super().__init__(session, Company)

    def get_by_code(self, code: str) -> Optional[Company]:
        """Get company by code."""
        return self.session.query(Company).filter(
            Company.code == code
        ).first()

    def get_by_name(self, name: str) -> Optional[Company]:
        """Get company by name."""
        return self.session.query(Company).filter(
            Company.name == name
        ).first()

    def get_all_active(self) -> List[Company]:
        """Get all active companies."""
        return self.session.query(Company).filter(
            Company.is_active == True
        ).order_by(Company.name).all()

    def get_all_ordered(self) -> List[Company]:
        """Get all companies ordered by name."""
        return self.session.query(Company).order_by(Company.name).all()

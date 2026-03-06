"""Base repository with common CRUD operations."""

from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from staffly.database.models.base import BaseModel

# Generic type for model
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.
    
    All specific repositories should inherit from this.
    """

    def __init__(self, session: Session, model: Type[ModelType]):
        """
        Initialize repository.
        
        Args:
            session: SQLAlchemy session
            model: The model class this repository manages
        """
        self.session = session
        self.model = model

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get a record by ID."""
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_all(self) -> List[ModelType]:
        """Get all records."""
        return self.session.query(self.model).all()

    def create(self, obj: ModelType) -> ModelType:
        """Create a new record."""
        self.session.add(obj)
        self.session.flush()  # Get the ID without committing
        return obj

    def update(self, obj: ModelType) -> ModelType:
        """Update an existing record."""
        self.session.merge(obj)
        self.session.flush()
        return obj

    def delete(self, obj: ModelType) -> None:
        """Delete a record."""
        self.session.delete(obj)
        self.session.flush()

    def delete_by_id(self, id: int) -> bool:
        """Delete a record by ID. Returns True if deleted, False if not found."""
        obj = self.get_by_id(id)
        if obj:
            self.delete(obj)
            return True
        return False

    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()

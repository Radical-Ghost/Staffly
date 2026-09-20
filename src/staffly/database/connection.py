"""Database connection and session management with encryption support."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


# Enable foreign key support for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class DatabaseManager:
    """
    Manages database connections and sessions with optional encryption.
    
    For LAN sharing, the database can be encrypted using SQLCipher.
    If pysqlcipher3 is available, encryption will be used.
    
    Usage:
        db = DatabaseManager()
        db.initialize("path/to/database.db", encryption_key="your-secret-key")
        
        with db.get_session() as session:
            # do database operations
            session.add(...)
            session.commit()
    """

    def __init__(self):
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None
        self._db_path: Path | None = None
        self._encryption_key: str | None = None
        self._is_encrypted: bool = False

    @property
    def is_initialized(self) -> bool:
        """Check if the database is initialized."""
        return self._engine is not None

    @property
    def db_path(self) -> Path | None:
        """Return the database file path."""
        return self._db_path
    
    @property
    def is_encrypted(self) -> bool:
        """Check if database is using encryption."""
        return self._is_encrypted

    def _check_sqlcipher_available(self) -> bool:
        """Check if SQLCipher (pysqlcipher3) is available."""
        try:
            import pysqlcipher3.dbapi2 as sqlcipher
            return True
        except ImportError:
            return False

    def initialize(
        self, 
        db_path: str | Path, 
        echo: bool = False,
        encryption_key: Optional[str] = None,
    ) -> None:
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file
            echo: If True, log all SQL statements (for debugging)
            encryption_key: Optional encryption key for SQLCipher encryption
        """
        self._db_path = Path(db_path)
        self._encryption_key = encryption_key
        
        # Ensure the directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if we should use encryption
        if encryption_key and self._check_sqlcipher_available():
            self._initialize_encrypted(echo)
        else:
            self._initialize_standard(echo)

    def _initialize_standard(self, echo: bool = False) -> None:
        """Initialize standard SQLite connection."""
        db_url = f"sqlite:///{self._db_path}"
        
        self._engine = create_engine(
            db_url,
            echo=echo,
            connect_args={"check_same_thread": False},
        )
        
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )
        self._is_encrypted = False

    def _initialize_encrypted(self, echo: bool = False) -> None:
        """Initialize encrypted SQLCipher connection."""
        try:
            import pysqlcipher3.dbapi2 as sqlcipher
            from sqlalchemy.pool import StaticPool
            
            def get_encrypted_connection():
                conn = sqlcipher.connect(str(self._db_path), check_same_thread=False)
                conn.execute(f"PRAGMA key='{self._encryption_key}'")
                conn.execute("PRAGMA foreign_keys=ON")
                return conn
            
            self._engine = create_engine(
                "sqlite://",
                echo=echo,
                creator=get_encrypted_connection,
                poolclass=StaticPool,
            )
            
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
            )
            self._is_encrypted = True
            
        except ImportError:
            # Fallback to standard if sqlcipher not available
            print("Warning: pysqlcipher3 not available, using unencrypted database")
            self._initialize_standard(echo)

    def create_tables(self) -> None:
        """Create all tables defined in the models."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        Base.metadata.create_all(self._engine)
        self._apply_schema_migrations()

    def _apply_schema_migrations(self) -> None:
        """Apply lightweight schema updates for existing SQLite databases."""
        if not self.is_initialized:
            return

        with self._engine.begin() as conn:
            # salary_structures.pf_employer
            columns = conn.execute(text("PRAGMA table_info(salary_structures)")).fetchall()
            column_names = {row[1] for row in columns}
            if "pf_employer" not in column_names:
                conn.execute(
                    text(
                        "ALTER TABLE salary_structures "
                        "ADD COLUMN pf_employer NUMERIC(12, 2) NOT NULL DEFAULT 0.00"
                    )
                )

            # monthly_payroll.arrears
            mp_columns = conn.execute(text("PRAGMA table_info(monthly_payroll)")).fetchall()
            mp_column_names = {row[1] for row in mp_columns}
            if "arrears" not in mp_column_names:
                conn.execute(
                    text(
                        "ALTER TABLE monthly_payroll "
                        "ADD COLUMN arrears NUMERIC(12, 2) NOT NULL DEFAULT 0.00"
                    )
                )

    def drop_tables(self) -> None:
        """Drop all tables (use with caution!)."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        Base.metadata.drop_all(self._engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session as a context manager.
        
        Usage:
            with db.get_session() as session:
                session.add(obj)
                session.commit()
        
        Yields:
            SQLAlchemy Session object
        """
        if not self.is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def session(self) -> Session:
        """
        Get a new session directly (caller is responsible for closing).
        
        For most cases, prefer get_session() context manager.
        
        Returns:
            SQLAlchemy Session object
        """
        if not self.is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self._session_factory()

    def close(self) -> None:
        """Close the database connection."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global database instance (singleton pattern)
db = DatabaseManager()


def get_db() -> DatabaseManager:
    """Get the global database manager instance."""
    return db


def init_db(
    db_path: str | Path, 
    echo: bool = False,
    encryption_key: Optional[str] = None,
) -> DatabaseManager:
    """
    Initialize the global database instance.
    
    Args:
        db_path: Path to the SQLite database file
        echo: If True, log all SQL statements
        encryption_key: Optional encryption key for SQLCipher
    
    Returns:
        The initialized DatabaseManager instance
    """
    db.initialize(db_path, echo=echo, encryption_key=encryption_key)
    db.create_tables()
    return db

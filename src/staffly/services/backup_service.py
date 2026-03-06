"""Database backup and restore service."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from staffly.database import get_db


class BackupService:
    """
    Service for database backup and restore operations.
    
    Provides:
    - Create timestamped backups
    - Restore from backup
    - List available backups
    - Auto-cleanup old backups
    """
    
    BACKUP_FOLDER_NAME = "backups"
    MAX_BACKUPS = 10  # Keep last N backups
    
    def __init__(self, data_path: Path | None = None):
        """
        Initialize backup service.
        
        Args:
            data_path: Base data folder path. If None, uses the db's parent folder.
        """
        self._data_path = data_path
    
    @property
    def data_path(self) -> Path:
        """Get the data folder path."""
        if self._data_path:
            return self._data_path
        
        db = get_db()
        if db.db_path:
            return db.db_path.parent
        
        raise RuntimeError("Database not initialized and no data path provided")
    
    @property
    def backup_folder(self) -> Path:
        """Get the backup folder path."""
        return self.data_path / self.BACKUP_FOLDER_NAME
    
    def ensure_backup_folder(self) -> Path:
        """Ensure backup folder exists."""
        self.backup_folder.mkdir(parents=True, exist_ok=True)
        return self.backup_folder
    
    def create_backup(self, description: str = "") -> Path:
        """
        Create a backup of the current database.
        
        Args:
            description: Optional description to include in filename
        
        Returns:
            Path to the backup file
        """
        db = get_db()
        if not db.db_path or not db.db_path.exists():
            raise RuntimeError("Database file not found")
        
        self.ensure_backup_folder()
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desc_part = f"_{description}" if description else ""
        backup_name = f"staffly_backup_{timestamp}{desc_part}.db"
        backup_path = self.backup_folder / backup_name
        
        # Copy database file
        shutil.copy2(db.db_path, backup_path)
        
        # Cleanup old backups
        self._cleanup_old_backups()
        
        return backup_path
    
    def restore_backup(self, backup_path: Path) -> bool:
        """
        Restore database from a backup.
        
        WARNING: This will overwrite the current database!
        
        Args:
            backup_path: Path to the backup file to restore
        
        Returns:
            True if restore successful
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        db = get_db()
        if not db.db_path:
            raise RuntimeError("Database not initialized")
        
        # Create a backup of current state before restoring (safety net)
        try:
            self.create_backup(description="pre_restore")
        except Exception:
            pass  # Best effort
        
        # Close current connection
        db.close()
        
        # Copy backup over current database
        shutil.copy2(backup_path, db.db_path)
        
        # Reinitialize database
        db.initialize(db.db_path)
        
        return True
    
    def list_backups(self) -> List[dict]:
        """
        List available backups.
        
        Returns:
            List of backup info dictionaries with keys:
            - path: Path to backup file
            - name: Filename
            - created: Creation datetime
            - size: File size in bytes
        """
        if not self.backup_folder.exists():
            return []
        
        backups = []
        for file in sorted(self.backup_folder.glob("staffly_backup_*.db"), reverse=True):
            stat = file.stat()
            backups.append({
                "path": file,
                "name": file.name,
                "created": datetime.fromtimestamp(stat.st_mtime),
                "size": stat.st_size,
            })
        
        return backups
    
    def get_latest_backup(self) -> Optional[Path]:
        """Get the most recent backup file."""
        backups = self.list_backups()
        if backups:
            return backups[0]["path"]
        return None
    
    def delete_backup(self, backup_path: Path) -> bool:
        """Delete a specific backup."""
        if backup_path.exists() and backup_path.parent == self.backup_folder:
            backup_path.unlink()
            return True
        return False
    
    def _cleanup_old_backups(self):
        """Remove old backups, keeping only the most recent MAX_BACKUPS."""
        backups = self.list_backups()
        
        # Delete oldest backups beyond the limit
        for backup in backups[self.MAX_BACKUPS:]:
            try:
                backup["path"].unlink()
            except Exception:
                pass  # Best effort


def get_backup_service(data_path: Path | None = None) -> BackupService:
    """Get a backup service instance."""
    return BackupService(data_path)

# Database Migration Guide

## Alembic is now set up for managing database schema changes

### Making Schema Changes

When you need to modify the database:

1.  **Edit the model** (e.g., add a field to `employee.py`)
2.  **Generate migration:**
    
    ```bash
    uv run alembic revision --autogenerate -m "description of change"
    ```
    
3.  **Review the migration file** in `migrations/versions/`
4.  **Apply the migration:**
    
    ```bash
    uv run alembic upgrade head
    ```
    

### Common Commands

```bash
# Check current versionuv run alembic current# View migration historyuv run alembic history# Upgrade to latestuv run alembic upgrade head# Downgrade one versionuv run alembic downgrade -1# Downgrade to specific versionuv run alembic downgrade <revision_id>
```

### Example: Adding a New Field

If you want to add `middle_name` to Employee:

1.  Edit `src/staffly/database/models/employee.py`:
    
    ```python
    middle_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ```
    
2.  Generate migration:
    
    ```bash
    uv run alembic revision --autogenerate -m "add middle name to employee"
    ```
    

Apply:

```bash
uv run alembic upgrade head
```

**Your existing data will be preserved!** ✅
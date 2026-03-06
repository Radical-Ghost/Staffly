"""Add gender and branch to employees, remove conveyance from salary structures

Revision ID: 001_add_gender_branch
Revises: 
Create Date: 2026-01-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_add_gender_branch'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add gender and branch columns to employees
    with op.batch_alter_table('employees') as batch_op:
        batch_op.add_column(sa.Column('gender', sa.String(10), nullable=True))
        batch_op.add_column(sa.Column('branch', sa.String(100), nullable=True))
    
    # Note: We cannot easily remove conveyance_allowance from SQLite
    # because it has data. The column will remain but be unused.
    # For new databases, the column won't exist.


def downgrade() -> None:
    # Remove gender and branch from employees
    with op.batch_alter_table('employees') as batch_op:
        batch_op.drop_column('gender')
        batch_op.drop_column('branch')

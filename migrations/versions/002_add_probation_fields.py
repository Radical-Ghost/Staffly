"""Add probation fields to employee

Revision ID: 002_add_probation_fields
Revises: 16c21103cf7b
Create Date: 2026-09-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_probation_fields'
down_revision: Union[str, None] = '16c21103cf7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('employees') as batch_op:
        batch_op.add_column(sa.Column('is_on_probation', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('probation_end_date', sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('employees') as batch_op:
        batch_op.drop_column('probation_end_date')
        batch_op.drop_column('is_on_probation')
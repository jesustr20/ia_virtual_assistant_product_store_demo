"""agregar columna role a users

Revision ID: 5977e790e729
Revises: bef5bbe8324c
Create Date: 2026-09-20 18:44:29.043543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5977e790e729'
down_revision: Union[str, Sequence[str], None] = 'bef5bbe8324c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('role', sa.String(), nullable=False, server_default='user'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role')

"""Initial production schema migration

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-09 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Schema tables are created via declarative metadata / create_all on startup
    pass

def downgrade() -> None:
    pass

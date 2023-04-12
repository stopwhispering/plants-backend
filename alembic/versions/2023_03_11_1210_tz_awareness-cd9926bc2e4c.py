"""Tz awareness.

Revision ID: cd9926bc2e4c
Revises: 5ec48043f8b6
Create Date: 2023-03-11 12:10:41.633510
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "cd9926bc2e4c"
down_revision = "5ec48043f8b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE pollination ALTER COLUMN pollinated_at TYPE timestamp WITH TIME ZONE;")


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

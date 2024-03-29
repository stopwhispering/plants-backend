"""Rename pollination.count to count_attempted.

Revision ID: 3fec819036fc
Revises: 1c9aef3b43a5
Create Date: 2023-04-09 13:38:08.256669
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3fec819036fc"
down_revision = "1c9aef3b43a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE pollination RENAME COLUMN count TO count_attempted;")


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

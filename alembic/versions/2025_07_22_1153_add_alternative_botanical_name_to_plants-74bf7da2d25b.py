"""add alternative_botanical_name to plants

Revision ID: 74bf7da2d25b
Revises: 82ce0c90900b
Create Date: 2025-07-22 11:53:18.390880

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '74bf7da2d25b'
down_revision = '82ce0c90900b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('plants', sa.Column('alternative_botanical_name', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('plants', 'alternative_botanical_name')

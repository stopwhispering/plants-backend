"""name_published_in_year opt.

Revision ID: 3fa0140431d8
Revises: ba4038a16c0f
Create Date: 2023-11-16 18:55:54.706438
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3fa0140431d8'
down_revision = 'ba4038a16c0f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('taxon', 'name_published_in_year',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('taxon', 'name_published_in_year',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###
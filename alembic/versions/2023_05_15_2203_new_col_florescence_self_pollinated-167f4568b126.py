"""New col florescence.self_pollinated.

Revision ID: 167f4568b126
Revises: 73935307fedf
Create Date: 2023-05-15 22:03:42.629691
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "167f4568b126"
down_revision = "73935307fedf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("florescence", sa.Column("self_pollinated", sa.BOOLEAN(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("florescence", "self_pollinated")
    # ### end Alembic commands ###
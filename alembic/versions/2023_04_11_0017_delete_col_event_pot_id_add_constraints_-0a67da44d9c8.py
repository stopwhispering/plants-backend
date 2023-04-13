"""Delete col Event.pot_id , add constraints pt2.

Revision ID: 0a67da44d9c8
Revises: 2e2f04c40820
Create Date: 2023-04-11 00:17:29.035973
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0a67da44d9c8"
down_revision = "2e2f04c40820"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("pot", "event_id", existing_type=sa.INTEGER(), nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("pot", "event_id", existing_type=sa.INTEGER(), nullable=True)
    # ### end Alembic commands ###
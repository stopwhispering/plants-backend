"""add allowed uniform color

Revision ID: 8b48dda8861b
Revises: 265262ee2f76
Create Date: 2023-01-28 21:38:33.494543

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8b48dda8861b'
down_revision = '265262ee2f76'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass
    # ### commands auto generated by Alembic - please adjust! ###
    # op.execute("ALTER TYPE flowercolordifferentiation ADD VALUE 'UNIFORM'")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

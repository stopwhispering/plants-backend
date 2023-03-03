"""Make soilname unique.

Revision ID: 2251ed252fb3
Revises: c8f3b832ba07
Create Date: 2023-03-03 16:17:10.840423
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2251ed252fb3"
down_revision = "c8f3b832ba07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, "soil", ["soil_name"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "soil", type_="unique")
    # ### end Alembic commands ###
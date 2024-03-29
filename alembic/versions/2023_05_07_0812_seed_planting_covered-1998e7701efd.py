"""Seed_planting covered.

Revision ID: 1998e7701efd
Revises: 96fd7a34439c
Create Date: 2023-05-07 08:12:32.851058
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1998e7701efd"
down_revision = "96fd7a34439c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "seed_planting", sa.Column("covered", sa.BOOLEAN(), nullable=False, server_default="False")
    )
    op.execute("ALTER TABLE seed_planting ALTER COLUMN covered DROP DEFAULT;")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("seed_planting", "covered")
    # ### end Alembic commands ###

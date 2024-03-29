"""Seed_planting less strict.

Revision ID: accd42d1acbf
Revises: 1998e7701efd
Create Date: 2023-05-07 14:56:39.766059
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "accd42d1acbf"
down_revision = "1998e7701efd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("seed_planting", "sterilized", existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column("seed_planting", "soaked", existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column("seed_planting", "covered", existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column("seed_planting", "count_planted", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column("seed_planting", "soil_id", existing_type=sa.INTEGER(), nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("seed_planting", "soil_id", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column("seed_planting", "count_planted", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column("seed_planting", "covered", existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column("seed_planting", "soaked", existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column("seed_planting", "sterilized", existing_type=sa.BOOLEAN(), nullable=False)
    # ### end Alembic commands ###

"""Migrate pot.shape_top to enum.

Revision ID: e67f125b3b21
Revises: 4aebb2bed9bc
Create Date: 2023-03-03 12:37:23.342801
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e67f125b3b21"
down_revision = "4aebb2bed9bc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.dialects import postgresql

    op.execute(
        "UPDATE pot \
        SET shape_top = (CASE \
            WHEN shape_top = 'square' THEN 'SQUARE' \
            WHEN shape_top = 'round' THEN 'ROUND' \
            WHEN shape_top = 'oval' THEN 'OVAL' \
            WHEN shape_top = 'hexagonal' THEN 'HEXAGONAL' \
         END);"
    )
    enum_new_type = postgresql.ENUM(
        "HEXAGONAL", "OVAL", "ROUND", "SQUARE", name="fbshapetop"
    )
    enum_new_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE pot ALTER COLUMN shape_top TYPE fbshapetop USING shape_top::text::fbshapetop"
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
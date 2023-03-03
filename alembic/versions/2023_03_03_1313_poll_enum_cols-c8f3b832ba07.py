"""Poll. enum cols.

Revision ID: c8f3b832ba07
Revises: 1acc6ba22b44
Create Date: 2023-03-03 13:13:23.926141
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8f3b832ba07"
down_revision = "1acc6ba22b44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.dialects import postgresql

    op.execute(
        "UPDATE florescence \
        SET creation_context = (CASE \
            WHEN creation_context = 'import' THEN 'IMPORT' \
            WHEN creation_context = 'manual' THEN 'MANUAL' \
            WHEN creation_context = 'api' THEN 'API' \
         END);"
    )
    enum_new_type = postgresql.ENUM("API", "IMPORT", "MANUAL", name="context")
    enum_new_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE florescence ALTER COLUMN creation_context TYPE context USING creation_context::text::context"
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

"""Switch florescence_status to enum, new status aborted.

Revision ID: b944434abf76
Revises: 20e1b5087385
Create Date: 2023-02-04 13:38:56.015631
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from plants.modules.pollination.enums import FlorescenceStatus

# revision identifiers, used by Alembic.
revision = "b944434abf76"
down_revision = "20e1b5087385"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    florescencestatus = postgresql.ENUM(*FlorescenceStatus.get_names(), name="florescencestatus")
    florescencestatus.create(op.get_bind())

    op.alter_column(
        "florescence",
        "florescence_status",
        existing_type=sa.VARCHAR(length=100),
        nullable=False,
    )

    op.execute(
        "UPDATE florescence SET florescence_status = 'FLOWERING' "
        "WHERE florescence_status = 'flowering';"
    )
    op.execute(
        "UPDATE florescence SET florescence_status = 'INFLORESCENCE_APPEARED' "
        "WHERE florescence_status = 'inflorescence_appeared';"
    )
    op.execute(
        "UPDATE florescence SET florescence_status = 'FINISHED' "
        "WHERE florescence_status = 'finished';"
    )
    op.execute(
        "ALTER TABLE florescence ALTER COLUMN florescence_status "
        "TYPE florescencestatus USING florescence_status::florescencestatus;"
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "florescence",
        "florescence_status",
        existing_type=sa.VARCHAR(length=100),
        nullable=True,
    )
    # ### end Alembic commands ###

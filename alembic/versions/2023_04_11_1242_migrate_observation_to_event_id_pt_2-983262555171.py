"""Migrate observation to event_id pt 2.

Revision ID: 983262555171
Revises: 4741510b8ed1
Create Date: 2023-04-11 12:42:54.982601
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "983262555171"
down_revision = "4741510b8ed1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("DELETE FROM public.observation where event_id is null;")
    op.drop_constraint("event_observation_id_fkey", "event", type_="foreignkey")
    op.drop_column("event", "observation_id")
    op.alter_column(
        "observation", "event_id", existing_type=sa.INTEGER(), nullable=False
    )
    op.create_foreign_key(None, "observation", "event", ["event_id"], ["id"])

    #
    # --ORDER BY id ASC
    #


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "observation", type_="foreignkey")
    op.alter_column(
        "observation", "event_id", existing_type=sa.INTEGER(), nullable=True
    )
    op.add_column(
        "event",
        sa.Column("observation_id", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        "event_observation_id_fkey", "event", "observation", ["observation_id"], ["id"]
    )
    # ### end Alembic commands ###

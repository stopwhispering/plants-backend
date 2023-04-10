"""Undo.

Revision ID: 43dd09460f0c
Revises: f9d4504805d3
Create Date: 2023-04-10 12:47:07.861492
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "43dd09460f0c"
down_revision = "f9d4504805d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "image_to_event_association_event_id_fkey",
        "image_to_event_association",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None, "image_to_event_association", "event", ["event_id"], ["id"]
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "image_to_event_association", type_="foreignkey")
    op.create_foreign_key(
        "image_to_event_association_event_id_fkey",
        "image_to_event_association",
        "event",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###

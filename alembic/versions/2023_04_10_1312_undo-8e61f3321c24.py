"""Undo.

Revision ID: 8e61f3321c24
Revises: 0fe895aa4d93
Create Date: 2023-04-10 13:12:57.392044
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8e61f3321c24"
down_revision = "0fe895aa4d93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "image_to_event_association_event_id_fkey",
        "image_to_event_association",
        type_="foreignkey",
    )
    op.drop_constraint(
        "image_to_event_association_image_id_fkey",
        "image_to_event_association",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "image_to_event_association",
        "event",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "image_to_event_association",
        "image",
        ["image_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "image_to_event_association", type_="foreignkey")
    op.drop_constraint(None, "image_to_event_association", type_="foreignkey")
    op.create_foreign_key(
        "image_to_event_association_image_id_fkey",
        "image_to_event_association",
        "image",
        ["image_id"],
        ["id"],
    )
    op.create_foreign_key(
        "image_to_event_association_event_id_fkey",
        "image_to_event_association",
        "event",
        ["event_id"],
        ["id"],
    )
    # ### end Alembic commands ###
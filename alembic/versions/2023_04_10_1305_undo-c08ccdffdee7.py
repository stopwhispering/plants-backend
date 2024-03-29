"""Undo.

Revision ID: c08ccdffdee7
Revises: bb20f26f5b7e
Create Date: 2023-04-10 13:05:13.366898
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c08ccdffdee7"
down_revision = "bb20f26f5b7e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "image_to_event_association_image_id_fkey",
        "image_to_event_association",
        type_="foreignkey",
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
    op.create_foreign_key(
        "image_to_event_association_image_id_fkey",
        "image_to_event_association",
        "image",
        ["image_id"],
        ["id"],
    )
    # ### end Alembic commands ###

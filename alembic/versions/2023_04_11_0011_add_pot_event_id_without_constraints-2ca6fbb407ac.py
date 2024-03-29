"""Add Pot.event_id without constraints.

Revision ID: 2ca6fbb407ac
Revises: 8e61f3321c24
Create Date: 2023-04-11 00:11:20.167642
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2ca6fbb407ac"
down_revision = "8e61f3321c24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "image_to_event_association_image_id_fkey",
        "image_to_event_association",
        type_="foreignkey",
    )
    op.create_foreign_key(None, "image_to_event_association", "image", ["image_id"], ["id"])
    op.add_column("pot", sa.Column("event_id", sa.INTEGER(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("pot", "event_id")
    op.drop_constraint(None, "image_to_event_association", type_="foreignkey")
    op.create_foreign_key(
        "image_to_event_association_image_id_fkey",
        "image_to_event_association",
        "image",
        ["image_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###

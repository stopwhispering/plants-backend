"""Context to enum in db.

Revision ID: 63ef5b81cf02
Revises: 983262555171
Create Date: 2023-04-11 20:37:00.699097
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "63ef5b81cf02"
down_revision = "983262555171"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "image_to_event_association_event_id_fkey", "image_to_event_association", type_="foreignkey"
    )
    op.create_foreign_key(None, "image_to_event_association", "event", ["event_id"], ["id"])
    # ### end Alembic commands ###
    op.execute(
        "UPDATE florescence SET last_update_context = 'API' WHERE last_update_context = 'api';"
    )
    op.execute(
        "ALTER TABLE florescence ALTER COLUMN last_update_context TYPE context USING last_update_context::context;"
    )


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

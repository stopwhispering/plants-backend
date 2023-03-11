"""Preview_image_id not filenema.

Revision ID: a9180a2deedf
Revises: cd9926bc2e4c
Create Date: 2023-03-11 21:23:07.612124
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a9180a2deedf"
down_revision = "cd9926bc2e4c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("plants", sa.Column("preview_image_id", sa.INTEGER(), nullable=True))
    op.create_foreign_key(None, "plants", "image", ["preview_image_id"], ["id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "plants", type_="foreignkey")
    op.drop_column("plants", "preview_image_id")
    # ### end Alembic commands ###
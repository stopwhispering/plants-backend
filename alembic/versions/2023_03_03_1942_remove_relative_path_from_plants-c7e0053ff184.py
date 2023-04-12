"""Remove relative_path from plants.

Revision ID: c7e0053ff184
Revises: b2dbd040238b
Create Date: 2023-03-03 19:42:49.152457
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c7e0053ff184"
down_revision = "b2dbd040238b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("image", "relative_path")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "image",
        sa.Column("relative_path", sa.VARCHAR(length=240), autoincrement=False, nullable=False),
    )
    # ### end Alembic commands ###

"""Rename some datetime cols.

Revision ID: 1057e4b949db
Revises: 502609ab2a9a
Create Date: 2023-03-03 17:53:36.932097
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1057e4b949db"
down_revision = "502609ab2a9a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE plants RENAME last_update TO last_updated_at;")
    op.execute("ALTER TABLE image RENAME last_update TO last_updated_at;")
    op.execute("ALTER TABLE distribution RENAME last_update TO last_updated_at;")
    op.execute("ALTER TABLE soil RENAME last_update TO last_updated_at;")
    op.execute("ALTER TABLE pollination RENAME last_update TO last_updated_at;")
    op.execute("ALTER TABLE pot RENAME last_update TO last_updated_at;")
    op.execute("ALTER TABLE observation RENAME last_update TO last_updated_at;")
    op.execute("ALTER TABLE taxon RENAME last_update TO last_updated_at;")
    op.execute("ALTER TABLE tags RENAME last_update TO last_updated_at;")
    op.execute(
        "ALTER TABLE taxon_ocurrence_image RENAME last_update TO last_updated_at;"
    )
    op.execute("ALTER TABLE event RENAME last_update TO last_updated_at;")


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

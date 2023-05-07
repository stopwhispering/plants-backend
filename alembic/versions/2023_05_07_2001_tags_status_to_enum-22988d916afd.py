"""Tags.status to enum.

Revision ID: 22988d916afd
Revises: 39d0d2e94967
Create Date: 2023-05-07 20:01:28.094999
"""
from alembic import op
import sqlalchemy as sa

from plants.modules.plant.enums import TagState
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "22988d916afd"
down_revision = "39d0d2e94967"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###

    tagstate = postgresql.ENUM(*TagState.get_names(), name="tagstate")
    tagstate.create(op.get_bind())

    op.execute("UPDATE tags SET state = 'NONE' WHERE state = 'None';")
    op.execute("UPDATE tags SET state = 'INDICATION01' WHERE state = 'Indication01';")
    op.execute("UPDATE tags SET state = 'SUCCESS' WHERE state = 'Success';")
    op.execute("UPDATE tags SET state = 'INFORMATION' WHERE state = 'Information';")
    op.execute("UPDATE tags SET state = 'ERROR' WHERE state = 'Error';")
    op.execute("UPDATE tags SET state = 'WARNING' WHERE state = 'Warning';")
    op.execute("ALTER TABLE tags ALTER COLUMN state TYPE tagstate USING state::tagstate;")


def downgrade() -> None:
    pass
    # ### commands auto generated by Alembic - please adjust! ###
    # ### end Alembic commands ###

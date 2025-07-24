"""increase plant_name len in plants

Revision ID: baa3440dd7bb
Revises: bbad563717c7
Create Date: 2025-07-24 10:44:42.889548

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'baa3440dd7bb'
down_revision = 'bbad563717c7'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'plants',
        'plant_name',
        existing_type=sa.VARCHAR(length=100),
        type_=sa.VARCHAR(length=1000),
        existing_nullable=False,
    )

def downgrade():
    op.alter_column(
        'plants',
        'plant_name',
        existing_type=sa.VARCHAR(length=1000),
        type_=sa.VARCHAR(length=100),
        existing_nullable=False,
    )

"""remove properties models

Revision ID: bbceddd14edc
Revises: 2e57fa06f44d
Create Date: 2023-02-13 20:50:04.827240

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'bbceddd14edc'
down_revision = '2e57fa06f44d'
branch_labels = None
depends_on = None



def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('property_value')
    op.drop_table('property_name')
    op.drop_table('property_category')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('property_category',
    sa.Column('id', sa.INTEGER(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=True, cache=1), autoincrement=True, nullable=False),
    sa.Column('category_name', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
    sa.Column('last_update', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='property_category_pkey'),
    sa.UniqueConstraint('category_name', name='property_category_category_name_key'),
    postgresql_ignore_search_path=False
    )
    op.create_table('property_value',
    sa.Column('id', sa.INTEGER(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=True, cache=1), autoincrement=True, nullable=False),
    sa.Column('property_name_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('property_value', sa.VARCHAR(length=240), autoincrement=False, nullable=True),
    sa.Column('plant_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('taxon_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('last_update', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], name='property_value_plant_id_fkey'),
    sa.ForeignKeyConstraint(['property_name_id'], ['property_name.id'], name='property_value_property_name_id_fkey'),
    sa.ForeignKeyConstraint(['taxon_id'], ['taxon.id'], name='property_value_taxon_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='property_value_pkey')
    )
    op.create_table('property_name',
    sa.Column('id', sa.INTEGER(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=True, cache=1), autoincrement=True, nullable=False),
    sa.Column('property_name', sa.VARCHAR(length=240), autoincrement=False, nullable=False),
    sa.Column('category_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('last_update', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['property_category.id'], name='property_name_category_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='property_name_pkey')
    )
    # ### end Alembic commands ###

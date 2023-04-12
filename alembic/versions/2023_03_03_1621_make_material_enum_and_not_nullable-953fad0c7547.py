"""Make material enum and not nullable.

Revision ID: 953fad0c7547
Revises: 2251ed252fb3
Create Date: 2023-03-03 16:21:42.745636
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "953fad0c7547"
down_revision = "2251ed252fb3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("pot", "material", existing_type=sa.VARCHAR(length=50), nullable=False)
    # ### end Alembic commands ###
    from sqlalchemy.dialects import postgresql

    op.execute(
        "UPDATE pot \
        SET material = (CASE \
            WHEN material = 'Plastik' THEN 'PLASTIC' \
            WHEN material = 'Fruchtzwergbech' THEN 'PLASTIC' \
            WHEN material = 'Terrakotta' THEN 'TERRACOTTA' \
            WHEN material = 'Ton' THEN 'CLAY' \
         END);"
    )
    enum_new_type = postgresql.ENUM("CLAY", "PLASTIC", "TERRACOTTA", name="potmaterial")
    enum_new_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE pot ALTER COLUMN material TYPE potmaterial USING material::text::potmaterial"
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("pot", "material", existing_type=sa.VARCHAR(length=50), nullable=True)
    # ### end Alembic commands ###

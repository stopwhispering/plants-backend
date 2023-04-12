"""Pollination enum cols.

Revision ID: f7509236e341
Revises: a1c0f761afe0
Create Date: 2023-03-03 12:54:46.807110
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f7509236e341"
down_revision = "a1c0f761afe0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.dialects import postgresql

    op.execute(
        "UPDATE pollination \
        SET pollen_type = (CASE \
            WHEN pollen_type = 'fresh' THEN 'FRESH' \
            WHEN pollen_type = 'frozen' THEN 'FROZEN' \
            WHEN pollen_type = 'unknown' THEN 'UNKNOWN' \
         END);"
    )
    enum_new_type = postgresql.ENUM("FRESH", "FROZEN", "UNKNOWN", name="pollentype")
    enum_new_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE pollination ALTER COLUMN pollen_type TYPE pollentype USING pollen_type::text::pollentype"
    )

    op.execute(
        "UPDATE pollination \
        SET pollen_quality = (CASE \
            WHEN pollen_quality = 'good' THEN 'GOOD' \
            WHEN pollen_quality = 'bad' THEN 'BAD' \
            WHEN pollen_quality = 'unknown' THEN 'UNKNOWN' \
         END);"
    )
    enum_new_type = postgresql.ENUM("BAD", "GOOD", "UNKNOWN", name="pollenquality")
    enum_new_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE pollination ALTER COLUMN pollen_quality TYPE pollenquality USING pollen_quality::text::pollenquality"
    )

    op.execute(
        "UPDATE pollination \
        SET location = (CASE \
            WHEN location = 'unknown' THEN 'UNKNOWN' \
            WHEN location = 'indoor' THEN 'INDOOR' \
            WHEN location = 'outdoor' THEN 'OUTDOOR' \
            WHEN location = 'indoor_led' THEN 'INDOOR_LED' \
         END);"
    )
    enum_new_type = postgresql.ENUM("INDOOR", "INDOOR_LED", "OUTDOOR", "UNKNOWN", name="location")
    enum_new_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE pollination ALTER COLUMN location TYPE location USING location::text::location"
    )

    op.execute(
        "UPDATE pollination \
        SET pollination_status = (CASE \
            WHEN pollination_status = 'attempt' THEN 'ATTEMPT' \
            WHEN pollination_status = 'seed_capsule' THEN 'SEED_CAPSULE' \
            WHEN pollination_status = 'seed' THEN 'SEED' \
            WHEN pollination_status = 'germinated' THEN 'GERMINATED' \
            WHEN pollination_status = 'unknown' THEN 'UNKNOWN' \
            WHEN pollination_status = 'self_pollinated' THEN 'SELF_POLLINATED' \
         END);"
    )
    enum_new_type = postgresql.ENUM(
        "ATTEMPT",
        "GERMINATED",
        "SEED",
        "SEED_CAPSULE",
        "SELF_POLLINATED",
        "UNKNOWN",
        name="pollinationstatus",
    )
    enum_new_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE pollination ALTER COLUMN pollination_status TYPE pollinationstatus USING pollination_status::text::pollinationstatus"
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

from sqlalchemy import INTEGER, TEXT, VARCHAR, Column, Identity
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base


class History(Base):
    """History of certain events; used for error-finding et alia."""

    __tablename__ = "history"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )

    timestamp = Column(DateTime(timezone=True))  # todo rename
    plant_id = Column(INTEGER)
    plant_name = Column(VARCHAR(100))
    description = Column(TEXT)
    # type = Column(VARCHAR(40))  # Renaming, Plant Death, Gift  # implemented in plant model

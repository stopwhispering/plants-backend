from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.sql import sqltypes

from plants.modules.event.enums import PotMaterial
from plants.modules.event.models import Pot
from plants.modules.pollination.enums import Context, PollinationStatus
from plants.modules.pollination.models import Florescence, Pollination
from plants.modules.taxon.enums import FBRank
from plants.modules.taxon.models import Taxon

if TYPE_CHECKING:
    from enum import Enum


class EnumMigration:
    def __init__(self, enum: type[Enum], model: object):
        self.enum: type[Enum] = enum
        self.enum_type_name = self.enum.__name__.lower()
        self.temporary_enum_type_name = f"{self.enum_type_name}_old"
        self.table_name = model.__tablename__  # type: ignore[attr-defined]
        self.names: list[str] = self._get_names()
        self.enum_column_name = self._get_enum_column_name(model=model)

    def _get_enum_column_name(self, model: object) -> str:
        columns = list(model.__table__.columns)  # type: ignore[attr-defined]
        enum_columns = [
            column
            for column in columns
            if isinstance(column.type, sqltypes.Enum)
            and column.type.name == self.enum_type_name
        ]
        if not enum_columns:
            raise ValueError("No enum column found")
        if len(enum_columns) > 1:
            raise ValueError(
                "Not supported: " "More than one enum column with the same name"
            )
        return enum_columns[0].name  # type: ignore[no-any-return]

    def _get_names(self) -> list[str]:
        names = [
            f'"{name}"'
            for name, value in vars(self.enum).items()
            if type(value) is self.enum
        ]
        return sorted(names)

    @staticmethod
    def _print_imports() -> None:
        print("from sqlalchemy.dialects import postgresql")

    def _print_define_enum_type(self) -> None:
        print(
            f'enum_new_type = postgresql.ENUM({", ".join(self.names)}, '
            f'name="{self.enum_type_name}")'
        )

    def _print_create_enum_type_and_change_column(self) -> None:
        print("enum_new_type.create(op.get_bind())")
        print(
            f'op.execute("ALTER TABLE {self.table_name} ALTER COLUMN '
            f"{self.enum_column_name} TYPE {self.enum_type_name} USING "
            f'{self.enum_column_name}::text::{self.enum_type_name}")'
        )

    def print_upgrade_enum_type(self) -> None:
        """Alembic will not auto-detect a change of allowed enum values.

        The statements printed here are required to migrate the enum type.
        """
        self._print_header()
        self._print_imports()
        self._print_define_enum_type()
        print(
            f'op.execute("ALTER TYPE {self.enum_type_name} RENAME TO '
            f'{self.temporary_enum_type_name}")'
        )
        self._print_create_enum_type_and_change_column()
        print(f'op.execute("DROP TYPE {self.temporary_enum_type_name}")')

    @staticmethod
    def _print_header() -> None:
        print(
            """
        Copy & Paste the following lines into the alembic migration file:
        ---------------------------------------------------------------
        """
        )

    def _print_update_data(self) -> None:
        """If the column was type VARCHAR before and was filled with the enum's.

        <<values>>, we need to update the data to mach the enum's <<names>
        """
        # noinspection PyProtectedMember
        value_to_name = {
            value: name.name for value, name in self.enum._value2member_map_.items()
        }

        print(f'op.execute("UPDATE {self.table_name} \\')
        print(f"    SET {self.enum_column_name} = (CASE \\")
        for value, name in value_to_name.items():
            print(f"        WHEN {self.enum_column_name} = '{value}' THEN '{name}' \\")
        print('     END);")')

    def print_migrate_column_from_varchar_to_enum(self) -> None:
        """Alembic will not auto-detect a changed column from VARCHAR to Enum.

        The code printed here is required to create the eenm type, change the column
        type, and to migrate the data from VARCHAR to Enum. Enum columns require data to
        have the Enum <<names>> and not the Enum <<values>>.
        """
        self._print_header()
        self._print_imports()
        self._print_update_data()
        self._print_define_enum_type()
        self._print_create_enum_type_and_change_column()


if __name__ == "__main__":
    """
    Usage:
    # - Run `alembic revision --autogenerate -m "..."`
    # - Replace MyStatus and MyTable with your enum and model
    # - Comment out enum_migration.print_... line according to your scenario
    # - Copy & Paste the output into the alembic migration file
    # - Run `alembic upgrade head`
    """
    enum_migration = EnumMigration(enum=PotMaterial, model=Pot)
    enum_migration.print_migrate_column_from_varchar_to_enum()
    # enum_migration.print_upgrade_enum_type()

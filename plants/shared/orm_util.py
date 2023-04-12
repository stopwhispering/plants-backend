from __future__ import annotations

from typing import Any


def clone_orm_instance(model_instance: Any, clone_attrs: dict[str, Any] | None = None) -> Any:
    """Generate a transient clone of sqlalchemy instance; supply primary key as dict."""
    # get data of non-primary-key columns; exclude relationships
    table = model_instance.__table__
    non_pk_columns = [k for k in table.columns if k not in set(table.primary_key)]
    non_pk_column_names = [c.name for c in non_pk_columns]
    data = {c: getattr(model_instance, c) for c in non_pk_column_names}
    if clone_attrs:
        data.update(clone_attrs)
    return model_instance.__class__(**data)

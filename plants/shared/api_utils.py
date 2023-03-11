from __future__ import annotations

import json
from contextlib import suppress
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, overload

import pytz

from plants.shared.api_constants import FORMAT_API_YYYY_MM_DD_HH_MM, FORMAT_YYYY_MM_DD


def treat_non_serializable(x: Any) -> Any:
    """Tries to convert a supplied item into something that is json serializable."""
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    if isinstance(x, timedelta):
        return str(x)
    if isinstance(x, dict):
        make_dict_values_json_serializable(x)
        return x
    if isinstance(x, list):
        for i, li in enumerate(x):
            try:
                _ = json.dumps(li)
            except TypeError:
                x[i] = treat_non_serializable(li)
        return x
    if isinstance(x, Path):
        return x.as_posix()
    return str(x)


def make_list_items_json_serializable(items: list[Any]) -> None:
    """Tries to convert items in a supplied list into something that is json
    serializable."""
    for count, value in enumerate(items):
        if type(value) is dict:
            make_dict_values_json_serializable(items[count])
        else:
            try:
                _ = json.dumps(value)
            except TypeError:
                items[count] = treat_non_serializable(value)


def make_dict_values_json_serializable(d: dict[Any, Any]) -> None:
    """Tries to convert the values of a dict into something that is json serializable if
    it is not; works recursively for nested dicts, i.e. if value is also a dict."""
    for (
        key
    ) in (
        d
    ):  # can't loop at items() as value will then be a copy, not a reference to orig
        # obj
        if type(d[key]) is dict:
            make_dict_values_json_serializable(d[key])
        else:
            try:
                _ = json.dumps(d[key])
            except TypeError:
                d[key] = treat_non_serializable(d[key])


def parse_api_date(date_str: str | None) -> date | None:
    """Parse date from API request (e.g. '2022-11-16') to date object."""
    return (
        (
            datetime.strptime(date_str, FORMAT_YYYY_MM_DD)
            .astimezone(pytz.timezone("Europe/Berlin"))
            .date()
        )
        if date_str
        else None
    )


def format_api_date(d: date | None) -> str | None:
    """Format date from date object to API format (e.g. '2022-11-16')"""
    return d.strftime(FORMAT_YYYY_MM_DD) if d else None


def parse_api_datetime(dt_str: str) -> datetime:
    """Parse datetime from API request (e.g. '2022-11-16 23:59') to datetime object.

    the problem is that using astimezone() on a naive datetime object will assume that
    the datetime object is in local TZ, so we use pytz' localize() method
    """
    naive_dt = datetime.strptime(dt_str, FORMAT_API_YYYY_MM_DD_HH_MM)  # noqa: DTZ007
    return pytz.timezone("Europe/Berlin").localize(naive_dt)


@overload
def format_api_datetime(dt: datetime) -> str:
    ...


@overload
def format_api_datetime(dt: None) -> None:
    ...


def format_api_datetime(dt: datetime | None) -> str | None:
    """Format date from date object to API format (e.g. '2022-11-16 23:59')"""
    if not dt:
        return None
    return dt.astimezone(pytz.timezone("Europe/Berlin")).strftime(
        FORMAT_API_YYYY_MM_DD_HH_MM
    )


def date_hook(json_dict: dict[Any, Any]) -> dict[Any, Any]:
    """very simple hook to convert json date strings to datetime objects
    usage: json.loads(dumped_dict, object_hook=date_hook)"""
    for key, value in json_dict.items():
        try:
            json_dict[key] = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").astimezone(
                pytz.timezone("Europe/Berlin")
            )
        except Exception:
            with suppress(Exception):
                json_dict[key] = date.fromisoformat(value)
    return json_dict

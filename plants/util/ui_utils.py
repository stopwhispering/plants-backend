from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request
import json
from datetime import date, datetime, timedelta

from plants.schemas.shared import BMessageType, BMessage


def throw_exception(message: str = None,
                    message_type: BMessageType = BMessageType.ERROR,
                    additional_text: str = None,
                    status_code: int = 520,
                    description: str = None,
                    request: Request = None):
    """
    hands over supplied message details for ui5 frontend to be displayed as toast and added to message collection;
    adds header info from starlette request if available
    """
    description_text = ''
    if request:
        # todo remove? !
        description_text = f'Resource: {parse_resource_from_request(request)}'
    if description:
        description_text = description + '\n' + description_text
    raise HTTPException(detail={
        'type':           message_type.value,
        'message':        message,
        'additionalText': additional_text,
        'description':    description_text
        },
            status_code=status_code)


def get_message(message: str = None,
                message_type: BMessageType = BMessageType.INFORMATION,
                additional_text: str = None,
                description: str = None) -> dict:
    """generates a message to be userd in a ui5 frontend; uses flask request which is not required as a paramter"""
    msg = {
        'type':           message_type.value,
        'message':        message,
        'additionalText': additional_text,
        'description':    description
        }
    BMessage.validate(msg)
    return msg



def parse_resource_from_request(req: Request):
    items = req.get('path').split('/')
    index_start = items.index('api') + 1
    resource_name = '/'.join(items[index_start:])
    if '?' in resource_name:
        resource_name = resource_name[:resource_name.find('?')]

    return resource_name


def treat_non_serializable(x):
    """tries to convert a supplied item into something that is json serializable"""
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    elif isinstance(x, timedelta):
        return str(x)
    elif isinstance(x, dict):
        make_dict_values_json_serializable(x)
        return x
    elif isinstance(x, list):
        for i, l in enumerate(x):
            try:
                _ = json.dumps(l)
            except TypeError:
                x[i] = treat_non_serializable(l)
        return x
    elif isinstance(x, Path):
        return x.as_posix()
    else:
        return str(x)


def make_list_items_json_serializable(items: list):
    """tries to convert items in a supplied list into something that is json serializable"""
    for count, value in enumerate(items):
        if type(value) is dict:
            make_dict_values_json_serializable(items[count])
        else:
            try:
                _ = json.dumps(value)
            except TypeError:
                items[count] = treat_non_serializable(value)


def make_dict_values_json_serializable(d: dict):
    """tries to convert the values of a dict into something that is json serializable if it is not;
    works recursively for nested dicts, i.e. if value is also a dict"""
    for key in d.keys():  # can't loop at items() as value will then be a copy, not a reference to orig obj
        if type(d[key]) is dict:
            make_dict_values_json_serializable(d[key])
        else:
            try:
                _ = json.dumps(d[key])
            except TypeError:
                d[key] = treat_non_serializable(d[key])


def parse_api_date(date_str: str | None) -> date:
    """Parse date from API request (e.g. '2022-11-16') to date object"""
    if date_str:
        return datetime.strptime(date_str, FORMAT_YYYY_MM_DD).date()


def format_api_date(d: date) -> str:
    """Format date from date object to API format (e.g. '2022-11-16')"""
    if d:
        return d.strftime(FORMAT_YYYY_MM_DD)


def parse_api_datetime(dt_str: str | None) -> datetime:
    """Parse datetime from API request (e.g. '2022-11-16 23:59') to datetime object"""
    if dt_str:
        return datetime.strptime(dt_str, FORMAT_API_YYYY_MM_DD_HH_MM)


def format_api_datetime(dt: datetime) -> str:
    """Format date from date object to API format (e.g. '2022-11-16 23:59')"""
    if dt:
        return dt.strftime(FORMAT_API_YYYY_MM_DD_HH_MM)


FORMAT_YYYY_MM = '%Y-%m'
FORMAT_FULL_DATETIME = '%Y-%m-%d %H:%M:%S'
FORMAT_YYYY_MM_DD = '%Y-%m-%d'
FORMAT_API_YYYY_MM_DD_HH_MM = '%Y-%m-%d %H:%M'

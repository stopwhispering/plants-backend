from enum import Enum
from fastapi import HTTPException
from starlette.requests import Request
import json
from datetime import date, datetime, timedelta


class MessageType(Enum):
    """message types processed by error/success handlers in ui5 web frontend"""
    INFORMATION = 'Information'
    NONE = 'None'
    SUCCESS = 'Success'
    WARNING = 'Warning'
    ERROR = 'Error'
    DEBUG = 'Debug'  # not known by UI5 message processor, only showed in frontend console log


def throw_exception(message: str = None,
                    message_type: MessageType = MessageType.ERROR,
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
                message_type: MessageType = MessageType.INFORMATION,
                additional_text: str = None,
                description: str = None):
    """generates a message to be userd in a ui5 frontend; uses flask request which is not required as a paramter"""
    # description_text = f'Resource: {parse_resource_from_request(request)}'
    description_text = f'Resource: todo'
    if description and description.strip():
        description_text = description + '\n' + description_text
    return {
        'type':           message_type.value,
        'message':        message,
        'additionalText': additional_text,
        'description':    description_text
        }


def parse_resource_from_request(req: Request):
    items = req.get('path').split('/')
    index_start = items.index('backend') + 1
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

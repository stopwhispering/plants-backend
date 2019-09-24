from datetime import date, datetime, timedelta
import json
from flask import request
from flask_restful import abort
from enum import Enum

from plants_tagger.util.util import parse_resource_from_request


class MessageType(Enum):
    """message types processed by error/success handlers in web frontend"""
    INFORMATION = 'Information'
    NONE = 'None'
    SUCCESS = 'Success'
    WARNING = 'Warning'
    ERROR = 'Error'
    DEBUG = 'Debug'  # not known by UI5 message processor, only showed in frontend console log


def treat_non_serializable(x):
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


def make_list_items_json_serializable(l: list):
    for count, value in enumerate(l):
        if type(value) is dict:
            make_dict_values_json_serializable(l[count])
        else:
            try:
                _ = json.dumps(value)
            except TypeError:
                l[count] = treat_non_serializable(value)


def make_dict_values_json_serializable(d: dict):
    """converts values in a dict into strings if otherwies not seriazable,
    do it recursively for nested dicts, i.e. if value is also a dict"""
    for key in d.keys():  # can't loop at items() as value will then be a copy, not a reference to orig obj
        if type(d[key]) is dict:
            make_dict_values_json_serializable(d[key])
        else:
            try:
                _ = json.dumps(d[key])
            except TypeError:
                d[key] = treat_non_serializable(d[key])


def throw_exception(message: str = None,
                    message_type: MessageType = MessageType.ERROR,
                    additional_text: str = None,
                    status_code: int = 409,
                    description: str = None):
    """uses flask request, not required as a paramter"""
    description_text = f'Resource: {parse_resource_from_request(request)}'
    if description:
        description_text = description + '\n' + description_text
    abort(status_code, message={
                                'type':           message_type,
                                'message':        message,
                                'additionalText': additional_text,
                                'description':    description_text
                                })


def get_message(message: str = None,
                message_type: MessageType = MessageType.INFORMATION,
                additional_text: str = None,
                description: str = None):
    """uses flask request, not required as a paramter"""
    description_text = f'Resource: {parse_resource_from_request(request)}'
    if description and description.strip():
        description_text = description + '\n' + description_text
    return {
            'type':           message_type.value,
            'message':        message,
            'additionalText': additional_text,
            'description':    description_text
            }

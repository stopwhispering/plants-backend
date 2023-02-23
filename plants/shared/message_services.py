from fastapi import HTTPException
from starlette.requests import Request

from plants.shared.api_utils import parse_resource_from_request
from plants.shared.enums import BMessageType
from plants.shared.message_schemas import BMessage


def throw_exception(
    message: str = None,
    message_type: BMessageType = BMessageType.ERROR,
    additional_text: str = None,
    status_code: int = 520,
    description: str = None,
    request: Request = None,
):
    """
    hands over supplied message details for ui5 frontend to be displayed as toast and added to message collection;
    adds header info from starlette request if available
    """
    description_text = ""
    if request:
        # todo remove? !
        description_text = f"Resource: {parse_resource_from_request(request)}"
    if description:
        description_text = description + "\n" + description_text
    raise HTTPException(
        detail={
            "type": message_type.value,
            "message": message,
            "additionalText": additional_text,
            "description": description_text,
        },
        status_code=status_code,
    )


def get_message(
    message: str = None,
    message_type: BMessageType = BMessageType.INFORMATION,
    additional_text: str = None,
    description: str = None,
) -> dict:
    """generates a message to be userd in a ui5 frontend; uses flask request which is not required as a paramter"""
    msg = {
        "type": message_type.value,
        "message": message,
        "additionalText": additional_text,
        "description": description,
    }
    BMessage.validate(msg)
    return msg

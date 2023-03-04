from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from plants.shared.enums import MessageType
from plants.shared.message_schemas import BMessage


def throw_exception(
    message: str | None = None,
    message_type: MessageType = MessageType.ERROR,
    additional_text: str | None = None,
    status_code: int = 520,
    description: str | None = None,
) -> NoReturn:
    """Hands over supplied message details for ui5 frontend to be displayed as toast and
    added to message collection; adds header info from starlette request if
    available."""
    description_text = ""
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
    message: str | None = None,
    message_type: MessageType = MessageType.INFORMATION,
    additional_text: str | None = None,
    description: str | None = None,
) -> dict[str, str | None]:
    """Generates a message to be userd in a ui5 frontend; uses flask request which is
    not required as a paramter."""
    msg = {
        "type": message_type.value,
        "message": message,
        "additionalText": additional_text,
        "description": description,
    }
    BMessage.validate(msg)
    return msg

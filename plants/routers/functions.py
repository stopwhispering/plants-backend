from fastapi import APIRouter
import logging


logger = logging.getLogger(__name__)

router = APIRouter(
        tags=["functions"],
        responses={404: {"description": "Not found"}},
        )

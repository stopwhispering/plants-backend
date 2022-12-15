from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

import logging

from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from plants.extensions.auth import Token, authenticate_user, ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from plants.models.users import fake_users_db

logger = logging.getLogger(__name__)


router = APIRouter(
    tags=["oauth2", "authorization", "jwt"],
    responses={404: {"description": "Not found"}},
)


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

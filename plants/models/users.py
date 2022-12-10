from pydantic import BaseModel


fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        # "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "hashed_password": '$2b$12$JagIzxOdvQyj3K4WZjOTF.1d7h/ql3spE88xPhcAx0f11CKabWGxC',
        "disabled": False,
    },
    "admin": {
        "username": "admin",
        "full_name": "Admin A.",
        "email": "admin@example.com",
        # "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "hashed_password": '$2b$12$pEFnPUxyU.By5y2ZjcvQAO.hDG/qzzgEDx0rziXg1kFP0RYbhcJWa',
        "disabled": False,
    }
}


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


def get_user(db: dict, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

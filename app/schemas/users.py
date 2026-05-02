from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    first_name: Annotated[
        str, Field(..., min_length=1, max_length=100, description="Имя пользователя")
    ]
    last_name: Annotated[
        str,
        Field(..., min_length=1, max_length=100, description="Фамилия пользователя"),
    ]
    patronymic: Annotated[
        str | None,
        Field(default=None, max_length=100, description="Отчество пользователя"),
    ]
    email: Annotated[
        EmailStr, Field(..., max_length=255, description="Email пользователя")
    ]

    model_config = {"str_strip_whitespace": True}


class UserRead(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(UserBase):
    password: Annotated[
        str,
        Field(
            ...,
            min_length=8,
            max_length=128,
            description="Пароль пользователя",
        ),
    ]


class UserUpdate(BaseModel):
    first_name: Annotated[
        str | None,
        Field(
            default=None, min_length=1, max_length=100, description="Имя пользователя"
        ),
    ]
    last_name: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=100,
            description="Фамилия пользователя",
        ),
    ]
    patronymic: Annotated[
        str | None,
        Field(default=None, max_length=100, description="Отчество пользователя"),
    ]
    email: Annotated[
        EmailStr | None,
        Field(default=None, max_length=255, description="Email пользователя"),
    ]

    model_config = {"str_strip_whitespace": True}


class TokenInfo(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"

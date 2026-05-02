from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import oauth2_scheme
from app.helpers.tokens import create_access_refresh_tokens
from app.schemas.users import TokenInfo, UserCreate, UserRead
from app.services import auth

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRead,
    summary="Регистрация пользователя",
)
async def register(
    data: UserCreate,
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    return await auth_service.register_user(data=data)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenInfo,
    summary="Авторизация пользователя",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    user = UserRead.model_validate(
        await auth_service.authenticate_user(
            email=form_data.username,
            password=form_data.password,
        )
    )
    return create_access_refresh_tokens(user=user)


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenInfo,
    summary="Обновление access токена по refresh токену",
)
async def refresh(
    token: str = Depends(oauth2_scheme),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    user = UserRead.model_validate(
        await auth_service.get_current_refresh_user(token=token)
    )
    return create_access_refresh_tokens(user=user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход из системы",
)
async def logout(
    token: str = Depends(oauth2_scheme),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    await auth_service.logout(token=token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from fastapi import APIRouter, Depends, Response, status

from app.core.security import oauth2_scheme
from app.models.users import User
from app.schemas.users import UserRead, UserUpdate
from app.services import auth
from app.validations.rbac import validate_user_has_role

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserRead,
    summary="Информация о текущем пользователе",
)
async def me(
    token: str = Depends(oauth2_scheme),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    user = UserRead.model_validate(
        await auth_service.get_current_auth_user(token=token)
    )
    return user


@router.put(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserRead,
    summary="Обновить профиль текущего пользователя",
)
async def update_me(
    data: UserUpdate,
    token: str = Depends(oauth2_scheme),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    current_user: User = await auth_service.get_current_auth_user(token=token)
    updated_user = await auth_service.update_current_user(user=current_user, data=data)
    return UserRead.model_validate(updated_user)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Мягкое удаление текущего пользователя",
)
async def delete_me(
    token: str = Depends(oauth2_scheme),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    current_user: User = await auth_service.get_current_auth_user(token=token)
    await auth_service.deactivate_current_user(user=current_user, token=token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/check/admin",
    status_code=status.HTTP_200_OK,
    summary="Проверка доступа для роли admin",
)
async def check_admin_role(
    token: str = Depends(oauth2_scheme),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    current_user: User = await auth_service.get_current_auth_user(token=token)
    await validate_user_has_role(
        user=current_user,
        role_name="admin",
        session=auth_service.session,
    )
    return {"message": "admin access granted"}


@router.get(
    "/check/moderator",
    status_code=status.HTTP_200_OK,
    summary="Проверка доступа для роли moderator",
)
async def check_moderator_role(
    token: str = Depends(oauth2_scheme),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    current_user: User = await auth_service.get_current_auth_user(token=token)
    await validate_user_has_role(
        user=current_user,
        role_name="moderator",
        session=auth_service.session,
    )
    return {"message": "moderator access granted"}


@router.get(
    "/check/user",
    status_code=status.HTTP_200_OK,
    summary="Проверка доступа для роли user",
)
async def check_user_role(
    token: str = Depends(oauth2_scheme),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    current_user: User = await auth_service.get_current_auth_user(token=token)
    await validate_user_has_role(
        user=current_user,
        role_name="user",
        session=auth_service.session,
    )
    return {"message": "user access granted"}

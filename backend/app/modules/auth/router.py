from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import DB, CurrentUser, SettingsDep
from app.core.ratelimit import rate_limit
from app.modules.auth.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])
limited = [Depends(rate_limit("auth", per_minute=10))]


def get_service(db: DB, settings: SettingsDep) -> AuthService:
    return AuthService(db, settings)


Service = Annotated[AuthService, Depends(get_service)]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, dependencies=limited, summary="Create an account")
async def register(req: RegisterRequest, service: Service) -> AuthResponse:
    return await service.register(req)


@router.post("/login", response_model=AuthResponse, dependencies=limited, summary="Log in with email + password")
async def login(req: LoginRequest, service: Service) -> AuthResponse:
    return await service.login(req)


@router.post("/refresh", response_model=TokenPair, dependencies=limited, summary="Rotate tokens using a refresh token")
async def refresh(req: RefreshRequest, service: Service) -> TokenPair:
    return await service.refresh(req.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a refresh token")
async def logout(req: RefreshRequest, service: Service) -> None:
    await service.logout(req.refresh_token)


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT, summary="Change password (signs out other sessions)")
async def change_password(req: ChangePasswordRequest, user: CurrentUser, service: Service) -> None:
    await service.change_password(user, req)

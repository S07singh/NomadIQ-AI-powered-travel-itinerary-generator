"""Shared FastAPI dependencies."""

from typing import Annotated, Any

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.asynchronous.database import AsyncDatabase

from app.core.cache import Cache
from app.core.config import Settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.jobs import JobRunner
from app.core.security import ACCESS, decode_token
from app.core.utils import to_object_id
from app.providers.registry import Providers

_bearer = HTTPBearer(auto_error=False, description="Access token from /auth/login or /auth/register")


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_providers(request: Request) -> Providers:
    return request.app.state.providers


def get_jobs(request: Request) -> JobRunner:
    return request.app.state.jobs


def get_cache(db: Annotated[AsyncDatabase, Depends(get_db)]) -> Cache:
    return Cache(db)


DB = Annotated[AsyncDatabase, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
ProvidersDep = Annotated[Providers, Depends(get_providers)]
JobsDep = Annotated[JobRunner, Depends(get_jobs)]
CacheDep = Annotated[Cache, Depends(get_cache)]


async def get_current_user(
    db: DB,
    settings: SettingsDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, Any]:
    if creds is None:
        raise UnauthorizedError("Authentication required")
    payload = decode_token(settings, creds.credentials, ACCESS)
    user = await db["users"].find_one({"_id": to_object_id(payload["sub"], "User")})
    if user is None or not user.get("is_active", True):
        raise UnauthorizedError("User not found or disabled")
    return user


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        self.page = page
        self.limit = limit


PageParams = Annotated[Pagination, Depends()]

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import DB, CurrentUser
from app.modules.users.schemas import (
    DeviceOut,
    DeviceRegister,
    TravelerCreate,
    TravelerOut,
    TravelerUpdate,
    UserOut,
    UserUpdate,
)
from app.modules.users.service import UserService, to_user_out

router = APIRouter(prefix="/users", tags=["Users"])


def get_service(db: DB) -> UserService:
    return UserService(db)


Service = Annotated[UserService, Depends(get_service)]


@router.get("/me", response_model=UserOut, summary="Current user profile")
async def get_me(user: CurrentUser) -> UserOut:
    return to_user_out(user)


@router.patch("/me", response_model=UserOut, summary="Update profile / preferences")
async def update_me(data: UserUpdate, user: CurrentUser, service: Service) -> UserOut:
    return await service.update_profile(user, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete account and personal data")
async def delete_me(user: CurrentUser, service: Service) -> None:
    await service.delete_account(user)


@router.get("/me/travelers", response_model=list[TravelerOut], summary="List saved travelers")
async def list_travelers(user: CurrentUser, service: Service) -> list[TravelerOut]:
    return await service.list_travelers(user)


@router.post("/me/travelers", response_model=TravelerOut, status_code=status.HTTP_201_CREATED, summary="Save a traveler profile")
async def create_traveler(data: TravelerCreate, user: CurrentUser, service: Service) -> TravelerOut:
    return await service.create_traveler(user, data)


@router.patch("/me/travelers/{traveler_id}", response_model=TravelerOut, summary="Update a saved traveler")
async def update_traveler(traveler_id: str, data: TravelerUpdate, user: CurrentUser, service: Service) -> TravelerOut:
    return await service.update_traveler(user, traveler_id, data)


@router.delete("/me/travelers/{traveler_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a saved traveler")
async def delete_traveler(traveler_id: str, user: CurrentUser, service: Service) -> None:
    await service.delete_traveler(user, traveler_id)


@router.post("/me/devices", response_model=DeviceOut, summary="Register a push-notification device")
async def register_device(data: DeviceRegister, user: CurrentUser, service: Service) -> DeviceOut:
    return await service.register_device(user, data)


@router.delete("/me/devices/{token}", status_code=status.HTTP_204_NO_CONTENT, summary="Unregister a device")
async def remove_device(token: str, user: CurrentUser, service: Service) -> None:
    await service.remove_device(user, token)

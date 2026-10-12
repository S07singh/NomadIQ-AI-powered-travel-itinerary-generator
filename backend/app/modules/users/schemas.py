from datetime import date, datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.common.schemas import APIModel, TravelStyle
from app.common.travel import TravelerInfo


class UserPreferences(APIModel):
    home_city: str | None = Field(default=None, max_length=100)
    home_airport: str | None = Field(default=None, min_length=3, max_length=3, description="IATA code")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    language: str = Field(default="en", max_length=10)
    travel_style: TravelStyle = TravelStyle.comfort
    dietary: list[str] = Field(default_factory=list, max_length=10, examples=[["vegetarian"]])
    interests: list[str] = Field(default_factory=list, max_length=20)
    notifications_enabled: bool = True


class UserPreferencesUpdate(APIModel):
    home_city: str | None = Field(default=None, max_length=100)
    home_airport: str | None = Field(default=None, min_length=3, max_length=3)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    language: str | None = Field(default=None, max_length=10)
    travel_style: TravelStyle | None = None
    dietary: list[str] | None = Field(default=None, max_length=10)
    interests: list[str] | None = Field(default=None, max_length=20)
    notifications_enabled: bool | None = None


class UserOut(APIModel):
    id: str
    email: EmailStr
    name: str
    avatar_url: str | None = None
    preferences: UserPreferences
    created_at: datetime


class UserUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=500)
    preferences: UserPreferencesUpdate | None = None


class TravelerCreate(TravelerInfo):
    """A saved traveler profile, reused for one-tap / voice bookings."""

    label: str = Field(default="", max_length=40, examples=["Me", "Mom"])


class TravelerUpdate(APIModel):
    label: str | None = Field(default=None, max_length=40)
    title: Literal["mr", "ms", "mrs", "miss", "dr"] | None = None
    given_name: str | None = Field(default=None, min_length=1, max_length=60)
    family_name: str | None = Field(default=None, min_length=1, max_length=60)
    born_on: date | None = None
    gender: Literal["m", "f", "x"] | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    nationality: str | None = Field(default=None, min_length=2, max_length=2)
    passport_number: str | None = Field(default=None, max_length=20)
    passport_expiry: date | None = None


class TravelerOut(TravelerCreate):
    id: str
    created_at: datetime


class DeviceRegister(APIModel):
    token: str = Field(min_length=10, max_length=500, description="Expo / FCM / APNs / Web Push token")
    platform: Literal["ios", "android", "web"]
    app_version: str | None = Field(default=None, max_length=20)


class DeviceOut(DeviceRegister):
    id: str
    created_at: datetime

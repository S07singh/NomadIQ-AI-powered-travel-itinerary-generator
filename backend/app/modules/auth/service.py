"""
Auth for web + mobile: short-lived JWT access tokens and rotating refresh tokens.
Refresh-token reuse (a revoked token presented again) revokes the whole family.
"""

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.core.config import Settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import ACCESS, REFRESH, create_token, decode_token, hash_password, verify_password
from app.core.utils import utcnow
from app.modules.auth.schemas import AuthResponse, ChangePasswordRequest, LoginRequest, RegisterRequest, TokenPair
from app.modules.users.schemas import UserPreferences
from app.modules.users.service import to_user_out


class AuthService:
    def __init__(self, db: AsyncDatabase, settings: Settings):
        self.db = db
        self.settings = settings

    async def register(self, req: RegisterRequest) -> AuthResponse:
        now = utcnow()
        user = {
            "email": req.email.lower(),
            "name": req.name.strip(),
            "password_hash": hash_password(req.password),
            "avatar_url": None,
            "preferences": UserPreferences().model_dump(mode="json"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.db["users"].insert_one(user)
        except DuplicateKeyError:
            raise ConflictError("An account with this email already exists", code="email_taken")
        user["_id"] = result.inserted_id
        return AuthResponse(user=to_user_out(user), tokens=await self.issue_tokens(result.inserted_id))

    async def login(self, req: LoginRequest) -> AuthResponse:
        user = await self.db["users"].find_one({"email": req.email.lower()})
        if not user or not verify_password(req.password, user.get("password_hash", "")):
            raise UnauthorizedError("Invalid email or password", code="invalid_credentials")
        if not user.get("is_active", True):
            raise UnauthorizedError("Account disabled", code="account_disabled")
        return AuthResponse(user=to_user_out(user), tokens=await self.issue_tokens(user["_id"]))

    async def issue_tokens(self, user_id: ObjectId) -> TokenPair:
        access, _, _ = create_token(self.settings, str(user_id), ACCESS)
        refresh, jti, expires = create_token(self.settings, str(user_id), REFRESH)
        await self.db["refresh_tokens"].insert_one(
            {"jti": jti, "user_id": user_id, "expires_at": expires, "revoked": False, "created_at": utcnow()}
        )
        return TokenPair(access_token=access, refresh_token=refresh, expires_in=self.settings.access_token_ttl_minutes * 60)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(self.settings, refresh_token, REFRESH)
        record = await self.db["refresh_tokens"].find_one_and_update(
            {"jti": payload["jti"], "revoked": False}, {"$set": {"revoked": True, "revoked_at": utcnow()}}
        )
        if record is None:
            # Unknown or already-used token: possible theft -> revoke every session of this user.
            await self.db["refresh_tokens"].update_many({"user_id": ObjectId(payload["sub"])}, {"$set": {"revoked": True}})
            raise UnauthorizedError("Refresh token is no longer valid", code="token_revoked")
        user = await self.db["users"].find_one({"_id": record["user_id"], "is_active": True})
        if user is None:
            raise UnauthorizedError("User not found or disabled")
        return await self.issue_tokens(record["user_id"])

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(self.settings, refresh_token, REFRESH)
        except UnauthorizedError:
            return  # already unusable
        await self.db["refresh_tokens"].update_one({"jti": payload["jti"]}, {"$set": {"revoked": True, "revoked_at": utcnow()}})

    async def change_password(self, user: dict, req: ChangePasswordRequest) -> None:
        if not verify_password(req.current_password, user.get("password_hash", "")):
            raise UnauthorizedError("Current password is incorrect", code="invalid_credentials")
        await self.db["users"].update_one(
            {"_id": user["_id"]}, {"$set": {"password_hash": hash_password(req.new_password), "updated_at": utcnow()}}
        )
        await self.db["refresh_tokens"].update_many({"user_id": user["_id"]}, {"$set": {"revoked": True}})

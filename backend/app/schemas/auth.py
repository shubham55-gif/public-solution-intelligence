"""Auth schemas: register, login, token response."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    role: str
    phone: str | None = None


class UserProfileResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    phone: str | None = None
    member_since: str
    total_reports: int = 0
    pending_reports: int = 0
    in_progress_reports: int = 0
    resolved_reports: int = 0


class AdminStatsResponse(BaseModel):
    total_citizens: int = 0
    total_admins: int = 0
    total_reports: int = 0
    pending: int = 0
    in_progress: int = 0
    resolved: int = 0
    high_risk: int = 0
    repeated: int = 0

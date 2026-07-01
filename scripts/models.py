"""Pydantic request/response schemas for the URL shortener API."""
from typing import Optional

from pydantic import BaseModel, Field


class ShortenRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    custom_alias: Optional[str] = Field(default=None, min_length=1, max_length=32)
    ttl_seconds: Optional[int] = Field(default=None, gt=0, le=31_536_000)  # max 1 year


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    long_url: str
    created_at: str
    expires_at: Optional[str]


class StatsResponse(BaseModel):
    code: str
    long_url: str
    created_at: str
    expires_at: Optional[str]
    clicks: int
    last_accessed_at: Optional[str]


class ErrorResponse(BaseModel):
    detail: str

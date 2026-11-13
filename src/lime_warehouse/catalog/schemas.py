from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(default="case", min_length=1, max_length=16)


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    unit: str | None = Field(default=None, min_length=1, max_length=16)
    is_active: bool | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name: str
    unit: str
    is_active: bool
    created_at: datetime


class LocationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    zone: str = Field(default="", max_length=32)
    kind: Literal["storage", "receiving"] = "storage"


class LocationUpdate(BaseModel):
    zone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    zone: str
    kind: str
    is_active: bool
    created_at: datetime

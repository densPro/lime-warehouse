from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PickLineIn(BaseModel):
    item_id: str
    location_id: str
    quantity: int = Field(gt=0)


class PickListCreate(BaseModel):
    reference: str = Field(default="", max_length=64)
    lines: list[PickLineIn] = Field(min_length=1)


class PickLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    location_id: str
    quantity: int
    picked_qty: int


class PickListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference: str
    status: str
    created_by: str
    created_at: datetime
    lines: list[PickLineOut]


class PickConfirm(BaseModel):
    quantity: int | None = Field(default=None, gt=0, description="Defaults to the whole remaining quantity")

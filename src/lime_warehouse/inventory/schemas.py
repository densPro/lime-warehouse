from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockLevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    location_id: str
    quantity: int
    updated_at: datetime


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    from_location_id: str | None
    to_location_id: str | None
    quantity: int
    movement_type: str
    reason: str
    reference_type: str | None
    reference_id: str | None
    actor_id: str
    request_id: str | None
    created_at: datetime

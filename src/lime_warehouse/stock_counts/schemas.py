from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class StockCountCreate(BaseModel):
    location_id: str


class CountedLine(BaseModel):
    item_id: str
    counted_qty: int = Field(ge=0, description="What was physically counted in the bin (0 = none found)")


class CountedLines(BaseModel):
    lines: list[CountedLine] = Field(min_length=1)


class StockCountLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    system_qty: int
    counted_qty: int | None
    adjustment_movement_id: str | None

    @computed_field
    @property
    def variance(self) -> int | None:
        return None if self.counted_qty is None else self.counted_qty - self.system_qty


class StockCountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    location_id: str
    status: str
    opened_by: str
    approved_by: str | None
    approval_reason: str
    created_at: datetime
    approved_at: datetime | None
    lines: list[StockCountLineOut]


class ApproveCount(BaseModel):
    reason: str = Field(
        min_length=3, max_length=500, description="Why the system quantities are being corrected"
    )

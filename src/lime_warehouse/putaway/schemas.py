from pydantic import BaseModel, Field


class PutawayCreate(BaseModel):
    item_id: str
    from_location_id: str
    to_location_id: str
    quantity: int = Field(gt=0)
    reason: str = Field(default="", max_length=500)

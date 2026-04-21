from pydantic import BaseModel, Field

class DemandRequest(BaseModel):
    predicted_demand: float = Field(..., ge=0)
    extra_order: int = Field(..., ge=0, le=1)
    month: int = Field(..., ge=1, le=12)
    day_of_week: int = Field(..., ge=0, le=6)
    day_of_month: int = Field(..., ge=1, le=31)
    is_weekend: int = Field(..., ge=0, le=1)
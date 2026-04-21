from pydantic import BaseModel, Field
from typing import List, Optional


class Customer(BaseModel):
    id: str
    lat: float
    lon: float
    name: Optional[str] = None             # ✅ added name (used in visualization)

    predicted_demand: float = Field(..., ge=0)
    extra_order: Optional[int] = Field(0, ge=0, le=1)  # ✅ now optional, defaults to 0

    month: int = Field(..., ge=1, le=12)
    day_of_week: int = Field(..., ge=0, le=6)
    day_of_month: int = Field(..., ge=1, le=31)

    is_weekend: int = Field(..., ge=0, le=1)


class Depot(BaseModel):
    lat: float
    lon: float


class FullRequest(BaseModel):
    depot: Depot
    customers: List[Customer]

    num_clusters: int = Field(..., ge=1)
    vehicle_capacity: int = Field(..., gt=0)
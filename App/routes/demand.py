from fastapi import APIRouter
from App.services.demand_service import predict_demand
from App.schemas.request_schema import DemandRequest

router = APIRouter()

@router.post("/predict-demand")
def predict(data: DemandRequest):
    
    features = [
        data.predicted_demand,
        data.extra_order,
        data.month,
        data.day_of_week,
        data.day_of_month,
        data.is_weekend
    ]

    result = predict_demand(features)

    return {
        "predicted_demand": result
    }
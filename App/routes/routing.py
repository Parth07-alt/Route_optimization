from fastapi import APIRouter
from App.services.routing_service import optimize_routes

router = APIRouter()

@router.post("/optimize-routes")
def optimize(data: dict):
    result = optimize_routes(data)
    return result
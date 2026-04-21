from fastapi import APIRouter
from fastapi.responses import FileResponse
from App.services.visualization_service import (
    create_base_map,
    plot_customers,
    plot_routes,
    save_map
)

router = APIRouter()

@router.post("/generate-map")
def generate_map(data: dict):
    """
    Accepts full pipeline output and generates a delivery map.

    Expected input:
    {
        "depot": {"lat": ..., "lon": ...},
        "customers": [...],
        "cluster_labels": [...],
        "routes": [...]
    }
    """

    depot = data["depot"]
    customers = data["customers"]
    cluster_labels = data["cluster_labels"]
    routes = data["routes"]

    # Build the map step by step
    m = create_base_map(depot)
    m = plot_customers(m, customers, cluster_labels)
    m = plot_routes(m, routes, customers, depot)

    # Save and return the HTML file
    output_path = save_map(m, "delivery_map.html")

    return FileResponse(
        path=output_path,
        media_type="text/html",
        filename="delivery_map.html"
    )
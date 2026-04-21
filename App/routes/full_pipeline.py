from fastapi import APIRouter, Depends
from datetime import date
from sqlalchemy.orm import Session
from App.services.demand_service import predict_demand
from App.services.routing_service import optimize_routes
from App.services.driver_service import assign_drivers
from App.services.db_service import save_delivery_session
from App.database.db import get_db
from data.drivers import drivers
from data.vehicles import vehicles
from App.schemas.full_schema import FullRequest
from App.services.visualization_service import (
    create_base_map, plot_customers, plot_routes, save_map, inject_legend
)
from App.services.db_service import (
    save_delivery_session,
    get_todays_orders,
    get_registered_customer,
    mark_orders_assigned,
    save_delivery_statuses,
    get_customers_by_session
)

router = APIRouter()


@router.post("/full-optimization")
def full_pipeline(data: FullRequest, db: Session = Depends(get_db)):

    data_dict = data.dict()
    customers = data_dict["customers"]
    depot = data_dict["depot"]

    # STEP 1: Demand Prediction
    for customer in customers:
        features = [
            customer["predicted_demand"],
            0,
            customer["month"],
            customer["day_of_week"],
            customer["day_of_month"],
            customer["is_weekend"]
        ]
        predicted = predict_demand(features)
        customer["demand"] = float(predicted)

    # STEP 2: Route Optimization
    routes = optimize_routes(data_dict)

    print("=== ROUTES DEBUG (full-optimization) ===")
    for cluster in routes["clusters"]:
        print(
            f"Cluster {cluster['cluster_id']}: "
            f"distance={cluster['distance_km']} km, "
            f"num_trips={cluster.get('num_trips')}, "
            f"total_demand={cluster.get('total_demand')}"
        )
        for r in cluster.get("routes", []):
            print(f"  Trip {r.get('trip_id')}: {r.get('route')}")
    print("=========================================")

    # STEP 3: Driver Assignment
    driver_assignments = assign_drivers(
        routes["clusters"],
        drivers,
        vehicles,
        customers,
        vehicle_capacity_per_trip=data_dict["vehicle_capacity"]
    )

    # STEP 4: Map Visualization
    cluster_labels = [customer["cluster"] for customer in customers]
    m = create_base_map(depot)
    m = plot_customers(m, customers, cluster_labels)
    m = plot_routes(m, routes["clusters"], customers, depot, driver_assignments)
    output_path = save_map(m, "delivery_map.html")
    inject_legend(output_path, routes["clusters"], driver_assignments)

    # STEP 5: Save to Database
    session_id = save_delivery_session(
        db=db,
        data=data_dict,
        customers=customers,
        routes=routes,
        driver_assignments=driver_assignments
    )

    save_delivery_statuses(
        db=db,
        session_id=session_id,
        routes=routes,
        driver_assignments=driver_assignments,
        customers=customers
    )

    return {
        "session_id": session_id,
        "routes": routes,
        "driver_assignments": driver_assignments,
        "map_url": "/static/delivery_map.html"
    }


@router.post("/optimize-from-orders")
def optimize_from_orders(
    request: dict,
    db: Session = Depends(get_db)
):
    from datetime import date, datetime, timezone, timedelta
    from App.services.db_service import (
        get_todays_orders_summed,
        get_todays_orders_for_rerun,
        get_registered_customer,
        mark_orders_assigned
    )

    force_rerun = request.get("force_rerun", False)

    if force_rerun:
        todays_orders = get_todays_orders_for_rerun(db)
    else:
        todays_orders = get_todays_orders_summed(db)

    if not todays_orders:
        return {"error": "No orders found for today!"}

    customers = []
    phone_numbers = []
    IST = timezone(timedelta(hours=5, minutes=30))

    for order in todays_orders:
        phone_number = order.phone_number
        total_cans = int(order.total_cans)

        registered = get_registered_customer(db, phone_number)

        if not registered:
            print(f"⚠️ Customer {phone_number} not registered — skipping")
            continue

        customers.append({
            "id": registered.customer_id,
            "name": registered.name,
            "lat": registered.lat,
            "lon": registered.lon,
            "predicted_demand": total_cans,
            "month": datetime.now(IST).month,
            "day_of_week": datetime.now(IST).weekday(),
            "day_of_month": datetime.now(IST).day,
            "is_weekend": 1 if datetime.now(IST).weekday() >= 5 else 0
        })
        phone_numbers.append(phone_number)

    if not customers:
        return {"error": "No registered customers found for today's orders!"}

    depot = request.get("depot", {"lat": 12.9716, "lon": 77.5946})
    vehicle_capacity = request.get("vehicle_capacity", 100)
    num_clusters = request.get("num_clusters", len(customers))
    num_clusters = min(num_clusters, len(customers))

    print(f"✅ Customers: {len(customers)}, Clusters: {num_clusters}, Vehicle capacity: {vehicle_capacity}")

    data_dict = {
        "depot": depot,
        "customers": customers,
        "num_clusters": num_clusters,
        "vehicle_capacity": vehicle_capacity
    }

    for customer in customers:
        customer["demand"] = float(customer["predicted_demand"])

    routes = optimize_routes(data_dict)

    print("=== ROUTES DEBUG (optimize-from-orders) ===")
    for cluster in routes["clusters"]:
        print(
            f"Cluster {cluster['cluster_id']}: "
            f"distance={cluster['distance_km']} km, "
            f"num_trips={cluster.get('num_trips')}, "
            f"total_demand={cluster.get('total_demand')}"
        )
        for r in cluster.get("routes", []):
            print(f"  Trip {r.get('trip_id')}: {r.get('route')}")
    print("===========================================")

    driver_assignments = assign_drivers(
        routes["clusters"],
        drivers,
        vehicles,
        customers,
        vehicle_capacity_per_trip=vehicle_capacity
    )

    print("=== DRIVER ASSIGNMENTS ===")
    for d_id, d_info in driver_assignments.items():
        print(f"  {d_id}: {d_info}")
    print("==========================")

    cluster_labels = [customer["cluster"] for customer in customers]
    m = create_base_map(depot)
    m = plot_customers(m, customers, cluster_labels)
    m = plot_routes(m, routes["clusters"], customers, depot, driver_assignments)
    output_path = save_map(m, "delivery_map.html")
    inject_legend(output_path, routes["clusters"], driver_assignments)

    session_id = save_delivery_session(
        db=db,
        data=data_dict,
        customers=customers,
        routes=routes,
        driver_assignments=driver_assignments
    )

    save_delivery_statuses(
        db=db,
        session_id=session_id,
        routes=routes,
        driver_assignments=driver_assignments,
        customers=customers
    )

    if not force_rerun:
        mark_orders_assigned(db, phone_numbers)

    return {
        "session_id": session_id,
        "total_orders": len(todays_orders),
        "customers_included": len(customers),
        "customers_detail": [
            {
                "id": c["id"],
                "name": c["name"],
                "demand": c["demand"],
                "lat": c["lat"],
                "lon": c["lon"]
            } for c in customers
        ],
        "routes": routes,
        "driver_assignments": driver_assignments,
        "map_url": "/static/delivery_map.html"
    }


# ✅ FIXED — lat/lon now included in deliveries response
@router.get("/driver/{driver_id}/deliveries")
def get_driver_deliveries_endpoint(
    driver_id: str,
    db: Session = Depends(get_db)
):
    from App.services.db_service import get_driver_deliveries, get_latest_session_id

    session_id = get_latest_session_id(db)
    if not session_id:
        return {"error": "No sessions found!"}

    deliveries = get_driver_deliveries(db, driver_id, session_id)

    if not deliveries:
        return {
            "driver_id": driver_id,
            "session_id": session_id,
            "deliveries": [],
            "message": "No pending deliveries found!"
        }

    # ✅ Build customer coords lookup from session DB
    session_customers = get_customers_by_session(db, session_id)
    coords_map = {
        c.customer_id: {"lat": c.lat, "lon": c.lon}
        for c in session_customers
    }

    return {
        "driver_id": driver_id,
        "session_id": session_id,
        "deliveries": [
            {
                "id": d.id,
                "customer_id": d.customer_id,
                "customer_name": d.customer_name,
                "num_cans": d.num_cans,
                "status": d.status,
                "cluster_id": d.cluster_id,
                "lat": coords_map.get(d.customer_id, {}).get("lat", None),  # ✅
                "lon": coords_map.get(d.customer_id, {}).get("lon", None)   # ✅
            }
            for d in deliveries
        ]
    }


@router.post("/driver/mark-delivered/{delivery_id}")
def mark_delivered_endpoint(
    delivery_id: int,
    db: Session = Depends(get_db)
):
    from App.services.db_service import mark_stop_delivered
    success = mark_stop_delivered(db, delivery_id)
    if success:
        return {"message": "Marked as delivered!", "delivery_id": delivery_id}
    return {"error": "Delivery not found!"}


@router.get("/driver/{driver_id}/progress/{session_id}")
def get_driver_progress_endpoint(
    driver_id: str,
    session_id: int,
    db: Session = Depends(get_db)
):
    from App.services.db_service import get_driver_progress
    return get_driver_progress(db, driver_id, session_id)   
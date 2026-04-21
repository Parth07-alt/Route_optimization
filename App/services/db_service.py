from sqlalchemy.orm import Session
from App.database.models import DeliverySession, Customer, Route, DriverAssignment
from datetime import datetime
from App.database.models import CustomerRegistry, Order
from datetime import date
from App.database.models import DeliveryStatus

def save_delivery_session(db: Session, data: dict, customers: list, routes: dict, driver_assignments: dict) -> int:
    """
    Saves complete pipeline result to database.
    Returns session_id for reference.
    """

    # =========================
    # 1. Save Delivery Session
    # =========================
    session = DeliverySession(
        created_at=datetime.utcnow(),
        depot_lat=data["depot"]["lat"],
        depot_lon=data["depot"]["lon"],
        num_clusters=data["num_clusters"],
        vehicle_capacity=data["vehicle_capacity"],
        total_customers=len(customers)
    )
    db.add(session)
    db.flush()

    # =========================
    # 2. Save Customers
    # =========================
    for customer in customers:
        db_customer = Customer(
            session_id=session.id,
            customer_id=customer["id"],
            name=customer.get("name", None),
            lat=customer["lat"],
            lon=customer["lon"],
            predicted_demand=customer["predicted_demand"],
            actual_demand=customer.get("demand", 0),
            cluster_id=customer.get("cluster", -1)
        )
        db.add(db_customer)

    # =========================
    # 3. Save Routes
    # =========================
    for cluster in routes["clusters"]:
        cluster_routes = cluster.get("routes", [])

        if not cluster_routes and "route" in cluster:
            cluster_routes = [{"trip_id": 0, "route": cluster["route"]}]

        for trip_route in cluster_routes:
            trip_id = trip_route.get("trip_id", trip_route.get("vehicle_id", 0))

            db_route = Route(
                session_id=session.id,
                cluster_id=cluster["cluster_id"],
                vehicle_id=trip_id,
                route_stops=trip_route["route"],
                distance_km=cluster["distance_km"],
                total_demand=cluster.get("total_demand", 0),
                num_vehicles=cluster.get("num_trips", cluster.get("num_vehicles", 1))
            )
            db.add(db_route)

    # =========================
    # 4. Save Driver Assignments
    # =========================
    for driver_id, assignment in driver_assignments.items():
        if driver_id.startswith("UNASSIGNED"):
            continue

        db_assignment = DriverAssignment(
            session_id=session.id,
            driver_id=driver_id,
            cluster_id=assignment["cluster_id"],
            num_vehicles=assignment.get("num_trips", assignment.get("num_vehicles", 1)),
            total_demand=assignment.get("total_demand", 0),
            vehicle_capacity=assignment.get("vehicle_capacity", 0),
            distance_to_cluster_km=assignment.get("distance_to_cluster_km", 0)
        )
        db.add(db_assignment)

    # =========================
    # 5. Commit Everything
    # =========================
    db.commit()
    db.refresh(session)

    return session.id


def get_all_sessions(db: Session):
    """Get all delivery sessions."""
    return db.query(DeliverySession).order_by(
        DeliverySession.created_at.desc()
    ).all()


def get_session_by_id(db: Session, session_id: int):
    """Get full details of a specific session."""
    return db.query(DeliverySession).filter(
        DeliverySession.id == session_id
    ).first()


def get_routes_by_session(db: Session, session_id: int):
    """Get all routes for a session."""
    return db.query(Route).filter(
        Route.session_id == session_id
    ).all()


def get_customers_by_session(db: Session, session_id: int):
    """Get all customers for a session."""
    return db.query(Customer).filter(
        Customer.session_id == session_id
    ).all()


def get_driver_assignments_by_session(db: Session, session_id: int):
    """Get all driver assignments for a session."""
    return db.query(DriverAssignment).filter(
        DriverAssignment.session_id == session_id
    ).all()


def register_customer(db: Session, phone_number: str, name: str, lat: float, lon: float, customer_id: str):
    """Register a new customer with their location."""
    existing = db.query(CustomerRegistry).filter(
        CustomerRegistry.phone_number == phone_number
    ).first()

    if existing:
        existing.name = name
        existing.lat = lat
        existing.lon = lon
        db.commit()
        return existing

    customer = CustomerRegistry(
        phone_number=phone_number,
        customer_id=customer_id,
        name=name,
        lat=lat,
        lon=lon
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_todays_orders(db: Session):
    """Get all pending orders placed today."""
    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(IST).strftime("%Y-%m-%d")
    return db.query(Order).filter(
        Order.delivery_date == today,
        Order.status == "pending"
    ).all()


def get_todays_orders_summed(db: Session):
    """Get today's orders summed per customer."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func
    IST = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(IST).strftime("%Y-%m-%d")

    results = db.query(
        Order.phone_number,
        func.sum(Order.num_cans).label("total_cans")
    ).filter(
        Order.delivery_date == today,
        Order.status == "pending"
    ).group_by(Order.phone_number).all()

    return results


def get_todays_orders_for_rerun(db: Session):
    """Get today's orders for re-run — includes assigned orders too."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func
    IST = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(IST).strftime("%Y-%m-%d")

    results = db.query(
        Order.phone_number,
        func.sum(Order.num_cans).label("total_cans")
    ).filter(
        Order.delivery_date == today
    ).group_by(Order.phone_number).all()

    return results


def get_registered_customer(db: Session, phone_number: str):
    """Get customer details by phone number."""
    return db.query(CustomerRegistry).filter(
        CustomerRegistry.phone_number == phone_number
    ).first()


def get_all_registered_customers(db: Session):
    """Get all registered customers."""
    return db.query(CustomerRegistry).filter(
        CustomerRegistry.is_active == "yes"
    ).all()


def mark_orders_assigned(db: Session, phone_numbers: list):
    """Mark today's orders as assigned after optimization."""
    today = date.today().strftime("%Y-%m-%d")
    for phone in phone_numbers:
        orders = db.query(Order).filter(
            Order.phone_number == phone,
            Order.delivery_date == today,
            Order.status == "pending"
        ).all()
        for order in orders:
            order.status = "assigned"
    db.commit()


def save_delivery_statuses(db: Session, session_id: int, routes: dict, driver_assignments: dict, customers: list):
    """Save delivery status for each customer stop."""

    customer_map = {c["id"]: c for c in customers}

    for driver_id, assignment in driver_assignments.items():
        if driver_id.startswith("UNASSIGNED"):
            continue

        cluster_id = assignment["cluster_id"]

        for trip_route in assignment.get("routes", []):
            for stop in trip_route["route"]:
                if stop == "DEPOT":
                    continue

                customer = customer_map.get(stop, {})

                db_status = DeliveryStatus(
                    session_id=session_id,
                    customer_id=stop,
                    customer_name=customer.get("name", None),
                    driver_id=driver_id,
                    cluster_id=cluster_id,
                    num_cans=int(customer.get("demand", 0)),
                    status="pending"
                )
                db.add(db_status)

    db.commit()


def get_driver_deliveries(db: Session, driver_id: str, session_id: int = None):
    """Get all deliveries assigned to a driver."""
    query = db.query(DeliveryStatus).filter(
        DeliveryStatus.driver_id == driver_id,
        DeliveryStatus.status == "pending"
    )
    if session_id:
        query = query.filter(DeliveryStatus.session_id == session_id)
    return query.order_by(DeliveryStatus.session_id.desc()).all()


def get_latest_session_id(db: Session):
    """Get the most recent session ID."""
    from App.database.models import DeliverySession
    session = db.query(DeliverySession).order_by(
        DeliverySession.created_at.desc()
    ).first()
    return session.id if session else None


def mark_stop_delivered(db: Session, delivery_id: int):
    """Mark a specific stop as delivered."""
    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))

    delivery = db.query(DeliveryStatus).filter(
        DeliveryStatus.id == delivery_id
    ).first()

    if delivery:
        delivery.status = "delivered"
        delivery.delivered_at = datetime.now(IST)
        db.commit()
        return True
    return False


def get_driver_progress(db: Session, driver_id: str, session_id: int):
    """Get delivery progress for a driver."""
    total = db.query(DeliveryStatus).filter(
        DeliveryStatus.driver_id == driver_id,
        DeliveryStatus.session_id == session_id
    ).count()

    delivered = db.query(DeliveryStatus).filter(
        DeliveryStatus.driver_id == driver_id,
        DeliveryStatus.session_id == session_id,
        DeliveryStatus.status == "delivered"
    ).count()

    return {"total": total, "delivered": delivered, "pending": total - delivered}
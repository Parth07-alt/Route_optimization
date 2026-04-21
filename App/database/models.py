from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from App.database.db import Base


class DeliverySession(Base):
    """Stores each full optimization run."""
    __tablename__ = "delivery_sessions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    depot_lat = Column(Float)
    depot_lon = Column(Float)
    num_clusters = Column(Integer)
    vehicle_capacity = Column(Integer)
    total_customers = Column(Integer)

    # Relationships
    customers = relationship("Customer", back_populates="session")
    routes = relationship("Route", back_populates="session")
    driver_assignments = relationship("DriverAssignment", back_populates="session")


class Customer(Base):
    """Stores each customer in a delivery session."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("delivery_sessions.id"))
    customer_id = Column(String)        # e.g. "C1"
    name = Column(String, nullable=True)
    lat = Column(Float)
    lon = Column(Float)
    predicted_demand = Column(Float)
    actual_demand = Column(Float)       # ML predicted value
    cluster_id = Column(Integer)

    # Relationship
    session = relationship("DeliverySession", back_populates="customers")


class Route(Base):
    """Stores each route per cluster per session."""
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("delivery_sessions.id"))
    cluster_id = Column(Integer)
    vehicle_id = Column(Integer)
    route_stops = Column(JSON)          # e.g. ["DEPOT", "C1", "C2", "DEPOT"]
    distance_km = Column(Float)
    total_demand = Column(Float)
    num_vehicles = Column(Integer)

    # Relationship
    session = relationship("DeliverySession", back_populates="routes")


class DriverAssignment(Base):
    """Stores driver assignment per cluster per session."""
    __tablename__ = "driver_assignments"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("delivery_sessions.id"))
    driver_id = Column(String)          # e.g. "D1"
    cluster_id = Column(Integer)
    num_vehicles = Column(Integer)
    total_demand = Column(Float)
    vehicle_capacity = Column(Integer)
    distance_to_cluster_km = Column(Float)

    # Relationship
    session = relationship("DeliverySession", back_populates="driver_assignments")


class Order(Base):
    """Stores customer orders received via WhatsApp."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    phone_number = Column(String)        # customer WhatsApp number
    customer_name = Column(String, nullable=True)
    num_cans = Column(Integer)           # how many cans ordered
    status = Column(String, default="pending")  # pending → assigned → delivered
    delivery_date = Column(String, nullable=True)  


class CustomerRegistry(Base):
    """Stores registered customers with their location."""
    __tablename__ = "customer_registry"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    phone_number = Column(String, unique=True)   # WhatsApp number
    customer_id = Column(String, unique=True)    # e.g. "C1", "C2"
    name = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    is_active = Column(String, default="yes")

class DeliveryStatus(Base):
    """Tracks delivery status per customer per session."""
    __tablename__ = "delivery_status"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("delivery_sessions.id"))
    customer_id = Column(String)
    customer_name = Column(String, nullable=True)
    driver_id = Column(String)
    cluster_id = Column(Integer)
    num_cans = Column(Integer)
    status = Column(String, default="pending")  # pending → delivered
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)

    session = relationship("DeliverySession", backref="delivery_statuses")          
import psycopg2
import pandas as pd

# ✅ Update with your password
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "water_distribution",
    "user": "postgres",
    "password": "Parth@123#"
}


def get_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(**DB_CONFIG)


def query_df(sql: str) -> pd.DataFrame:
    """Run SQL query and return DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()


def get_all_sessions():
    """Get all delivery sessions."""
    return query_df("""
        SELECT
            id,
            created_at,
            depot_lat,
            depot_lon,
            num_clusters,
            vehicle_capacity,
            total_customers
        FROM delivery_sessions
        ORDER BY created_at DESC
    """)


def get_session_customers(session_id: int):
    """Get all customers for a session."""
    return query_df(f"""
        SELECT
            customer_id,
            name,
            lat,
            lon,
            predicted_demand,
            actual_demand,
            cluster_id
        FROM customers
        WHERE session_id = {session_id}
        ORDER BY cluster_id, customer_id
    """)


def get_session_routes(session_id: int):
    """Get all routes for a session."""
    return query_df(f"""
        SELECT
            cluster_id,
            vehicle_id,
            route_stops,
            distance_km,
            total_demand,
            num_vehicles
        FROM routes
        WHERE session_id = {session_id}
        ORDER BY cluster_id, vehicle_id
    """)


def get_session_drivers(session_id: int):
    """Get all driver assignments for a session."""
    return query_df(f"""
        SELECT
            driver_id,
            cluster_id,
            num_vehicles,
            total_demand,
            vehicle_capacity,
            distance_to_cluster_km
        FROM driver_assignments
        WHERE session_id = {session_id}
        ORDER BY cluster_id
    """)


def get_analytics():
    """Get aggregated analytics data."""
    return query_df("""
        SELECT
            ds.id as session_id,
            ds.created_at,
            ds.total_customers,
            ds.num_clusters,
            ds.vehicle_capacity,
            COUNT(DISTINCT r.cluster_id) as total_clusters,
            SUM(r.distance_km) as total_distance,
            SUM(r.total_demand) as total_demand,
            SUM(r.num_vehicles) as total_vehicles
        FROM delivery_sessions ds
        LEFT JOIN routes r ON r.session_id = ds.id
        GROUP BY ds.id
        ORDER BY ds.created_at DESC
    """)
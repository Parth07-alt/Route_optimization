import streamlit as st
import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_all_sessions

API_URL = "http://127.0.0.1:8000"

# Driver + vehicle name lookup for display
DRIVER_INFO = {
    "D1": {"name": "Rahul", "vehicle": "Mini Truck (100 cap)"},
    "D2": {"name": "Amit", "vehicle": "Large Truck (200 cap)"},
    "D3": {"name": "Suresh", "vehicle": "Medium Truck (150 cap)"},
}


def show():
    st.title("📦 New Delivery Optimization")
    st.markdown("---")

    # ========================
    # SECTION 1 — MANUAL INPUT
    # ========================
    st.subheader("✍️ Manual Customer Input")

    col1, col2 = st.columns(2)
    with col1:
        depot_lat = st.number_input("Depot Latitude", value=12.9716, format="%.4f")
    with col2:
        depot_lon = st.number_input("Depot Longitude", value=77.5946, format="%.4f")

    col1, col2 = st.columns(2)
    with col1:
        num_clusters = st.slider("Number of Clusters", min_value=1, max_value=10, value=3)
    with col2:
        vehicle_capacity = st.slider("Vehicle Capacity (cans)", min_value=10, max_value=500, value=100)

    default_data = """C1,Rajesh Kumar,12.9800,77.5900,5
C2,Priya Sharma,12.9650,77.6000,3
C3,Amit Patel,12.9750,77.6100,7
C4,Sunita Rao,12.9600,77.5800,4
C5,Vikram Singh,12.9900,77.6050,6"""

    customer_input = st.text_area(
        "Format: ID, Name, Lat, Lon, Predicted Demand (one per line)",
        value=default_data,
        height=200
    )

    if st.button("🚀 Run Manual Optimization", type="primary"):
        with st.spinner("Running optimization..."):
            try:
                customers = []
                for line in customer_input.strip().split("\n"):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        customers.append({
                            "id": parts[0],
                            "name": parts[1],
                            "lat": float(parts[2]),
                            "lon": float(parts[3]),
                            "predicted_demand": float(parts[4]),
                            "month": 3,
                            "day_of_week": 1,
                            "day_of_month": 23,
                            "is_weekend": 0
                        })

                if not customers:
                    st.error("No valid customers found!")
                    return

                payload = {
                    "depot": {"lat": depot_lat, "lon": depot_lon},
                    "customers": customers,
                    "num_clusters": num_clusters,
                    "vehicle_capacity": vehicle_capacity
                }

                response = requests.post(
                    f"{API_URL}/full-optimization",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Optimization complete! Session ID: {result.get('session_id')}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("👥 Customers", len(customers))
                    with col2:
                        st.metric("🔵 Clusters", num_clusters)
                    with col3:
                        st.metric("🚚 Drivers Assigned", len(result["driver_assignments"]))

                    st.markdown("---")
                    st.subheader("🗺️ Delivery Map")
                    st.markdown(f"[Open Full Map]({API_URL}/static/delivery_map.html)")
                    st.components.v1.iframe(
                        f"{API_URL}/static/delivery_map.html",
                        height=500
                    )
                else:
                    st.error(f"API Error: {response.status_code} — {response.text}")

            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.markdown("---")
    st.markdown("---")

    # ========================
    # SECTION 2 — WHATSAPP ORDERS
    # ========================
    st.subheader("📱 Run Optimization from Today's WhatsApp Orders")
    st.info("This will automatically read today's WhatsApp orders and optimize routes.")

    col1, col2, col3 = st.columns(3)
    with col1:
        orders_depot_lat = st.number_input(
            "Depot Latitude ", value=12.9716,
            format="%.4f", key="orders_lat"
        )
    with col2:
        orders_depot_lon = st.number_input(
            "Depot Longitude ", value=77.5946,
            format="%.4f", key="orders_lon"
        )
    with col3:
        orders_vehicle_capacity = st.slider(
            "Vehicle Capacity",
            min_value=10, max_value=500,
            value=100, key="orders_capacity"
        )

    def run_optimization(force_rerun=False):
        payload = {
            "depot": {
                "lat": orders_depot_lat,
                "lon": orders_depot_lon
            },
            "vehicle_capacity": orders_vehicle_capacity,
            "force_rerun": force_rerun
        }
        response = requests.post(
            f"{API_URL}/optimize-from-orders",
            json=payload
        )
        return response

    def display_result(result):
        st.success(f"✅ Optimization complete! Session ID: {result['session_id']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 Total Orders", result["total_orders"])
        with col2:
            st.metric("👥 Customers", result["customers_included"])
        with col3:
            st.metric("🚚 Drivers Assigned", len(result["driver_assignments"]))

        st.markdown("---")
        st.subheader("👥 Customer Order Details")

        customers_detail = result.get("customers_detail", [])

        for cluster in result["routes"]["clusters"]:
            cluster_id = cluster["cluster_id"]
            num_trips = cluster.get("num_trips", 1)
            total_demand = cluster.get("total_demand", 0)
            distance_km = cluster.get("distance_km", 0)

            # Find assigned driver for this cluster
            assigned_driver_id = None
            assigned_driver_info = None
            for d_id, d_info in result["driver_assignments"].items():
                if isinstance(d_info, dict) and d_info.get("cluster_id") == cluster_id:
                    assigned_driver_id = d_id
                    assigned_driver_info = d_info
                    break

            # Build header
            if assigned_driver_id and not assigned_driver_id.startswith("UNASSIGNED"):
                info = DRIVER_INFO.get(assigned_driver_id, {})
                driver_display = (
                    f"{assigned_driver_id} — {info.get('name', '')} "
                    f"({info.get('vehicle', '')})"
                )
                st.markdown(f"### 🔵 Cluster {cluster_id} — Driver: {driver_display}")
            else:
                st.markdown(f"### 🔴 Cluster {cluster_id} — Driver: UNASSIGNED")

            # Trip summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔁 Trips Required", num_trips)
            with col2:
                st.metric("🪣 Total Demand", f"{total_demand} cans")
            with col3:
                st.metric("📏 Distance", f"{distance_km} km")

            if num_trips > 1:
                st.info(
                    f"ℹ️ {num_trips} trips needed — same driver makes "
                    f"{num_trips} sequential trips with the same vehicle."
                )

            # Show each trip and its stops
            for trip in cluster.get("routes", []):
                trip_id = trip.get("trip_id", trip.get("vehicle_id", "?"))
                stops = [s for s in trip["route"] if s != "DEPOT"]

                with st.expander(f"🚛 Trip {trip_id + 1} — {len(stops)} stop(s)", expanded=True):
                    for stop in stops:
                        customer_detail = next(
                            (c for c in customers_detail if c["id"] == stop), None
                        )
                        if customer_detail:
                            st.write(
                                f"📍 **{stop}** | "
                                f"{customer_detail['name']} | "
                                f"🪣 {customer_detail['demand']} cans | "
                                f"📌 ({customer_detail['lat']:.4f}, {customer_detail['lon']:.4f})"
                            )
                        else:
                            st.write(f"📍 {stop}")

            st.markdown("---")

        # Map
        st.subheader("🗺️ Delivery Map")
        st.markdown(f"[Open Full Map]({API_URL}/static/delivery_map.html)")
        st.components.v1.iframe(
            f"{API_URL}/static/delivery_map.html",
            height=500
        )

    if st.button("🚀 Run from WhatsApp Orders", type="primary", key="whatsapp_btn"):
        with st.spinner("Reading today's orders and optimizing..."):
            try:
                response = run_optimization(force_rerun=False)

                if response.status_code == 200:
                    result = response.json()

                    if "error" in result:
                        st.warning("⚠️ All orders for today are already assigned!")
                        st.info("Do you want to re-run optimization anyway?")

                        if st.button("🔄 Re-run Optimization", key="rerun_btn"):
                            with st.spinner("Re-running optimization..."):
                                rerun_response = run_optimization(force_rerun=True)
                                if rerun_response.status_code == 200:
                                    rerun_result = rerun_response.json()
                                    if "error" not in rerun_result:
                                        display_result(rerun_result)
                                    else:
                                        st.error(f"❌ {rerun_result['error']}")
                                else:
                                    st.error("Re-run failed!")
                    else:
                        display_result(result)

                else:
                    st.error(f"API Error: {response.status_code} — {response.text}")

            except Exception as e:
                st.error(f"Error: {str(e)}")
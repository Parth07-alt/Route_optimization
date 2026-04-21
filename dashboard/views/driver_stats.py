import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_all_sessions, get_session_drivers


def show():
    st.title("🚚 Driver Statistics")
    st.markdown("---")

    # Load sessions
    sessions = get_all_sessions()

    if sessions.empty:
        st.warning("No delivery sessions found. Run a delivery optimization first!")
        return

    # Session selector
    session_ids = sessions["id"].tolist()
    selected_session = st.selectbox(
        "Select Session",
        session_ids,
        format_func=lambda x: f"Session {x} — {str(sessions[sessions['id']==x]['created_at'].values[0])[:19]}"
    )

    # Load driver data
    drivers_df = get_session_drivers(selected_session)

    if drivers_df.empty:
        st.warning("No driver data found for this session.")
        return

    st.markdown("---")

    # ========================
    # DRIVER METRICS
    # ========================
    st.subheader("📊 Driver Performance Summary")

    cols = st.columns(len(drivers_df))
    for i, row in drivers_df.iterrows():
        with cols[i]:
            st.metric(f"🚚 {row['driver_id']}", f"{round(row['total_demand'], 2)} cans")
            st.caption(f"Cluster {row['cluster_id']} | {row['num_vehicles']} vehicle(s)")
            st.caption(f"📏 {row['distance_to_cluster_km']} km to cluster")

    st.markdown("---")

    # ========================
    # DRIVER TABLE
    # ========================
    st.subheader("📋 Full Driver Assignment Details")

    display_df = drivers_df.copy()
    display_df.columns = [
        "Driver", "Cluster", "Vehicles",
        "Total Demand", "Vehicle Capacity", "Distance to Cluster (km)"
    ]

    st.dataframe(display_df, use_container_width=True, hide_index=True)
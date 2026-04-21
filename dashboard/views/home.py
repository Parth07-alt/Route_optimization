import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_all_sessions, get_analytics


def show():
    st.title("🏠 Smart Water Distribution — Dashboard")
    st.markdown("---")

    # Load data
    sessions = get_all_sessions()
    analytics = get_analytics()

    if sessions.empty:
        st.warning("No delivery sessions found. Run a delivery optimization first!")
        return

    # ========================
    # TOP METRICS
    # ========================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📦 Total Sessions",
            value=len(sessions)
        )

    with col2:
        st.metric(
            label="👥 Total Customers Served",
            value=int(sessions["total_customers"].sum())
        )

    with col3:
        if not analytics.empty:
            total_distance = analytics["total_distance"].sum()
            st.metric(
                label="📏 Total Distance (km)",
                value=f"{round(total_distance, 2)}"
            )

    with col4:
        if not analytics.empty:
            total_vehicles = analytics["total_vehicles"].sum()
            st.metric(
                label="🚚 Total Vehicles Used",
                value=int(total_vehicles)
            )

    st.markdown("---")

    # ========================
    # RECENT SESSIONS TABLE
    # ========================
    st.subheader("📋 Recent Delivery Sessions")

    # Format the table
    display_df = sessions.copy()
    display_df["created_at"] = display_df["created_at"].astype(str)
    display_df.columns = [
        "Session ID", "Created At", "Depot Lat",
        "Depot Lon", "Clusters", "Vehicle Capacity", "Customers"
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # ========================
    # LATEST SESSION SUMMARY
    # ========================
    st.subheader("🔍 Latest Session Summary")

    latest = sessions.iloc[0]
    col1, col2 = st.columns(2)

    with col1:
        st.info(f"""
        **Session ID:** {latest['id']}
        **Date:** {str(latest['created_at'])[:19]}
        **Customers:** {latest['total_customers']}
        """)

    with col2:
        st.info(f"""
        **Clusters:** {latest['num_clusters']}
        **Vehicle Capacity:** {latest['vehicle_capacity']} cans
        **Depot:** ({latest['depot_lat']}, {latest['depot_lon']})
        """)
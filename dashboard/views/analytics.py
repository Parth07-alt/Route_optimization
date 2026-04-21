import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_analytics, get_all_sessions


def show():
    st.title("📊 Analytics")
    st.markdown("---")

    analytics = get_analytics()

    if analytics.empty:
        st.warning("No data found. Run some delivery optimizations first!")
        return

    # ========================
    # TOP METRICS
    # ========================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📦 Total Sessions", len(analytics))
    with col2:
        st.metric("👥 Total Customers", int(analytics["total_customers"].sum()))
    with col3:
        st.metric("📏 Total Distance (km)", round(analytics["total_distance"].sum(), 2))
    with col4:
        st.metric("🚚 Total Vehicles Used", int(analytics["total_vehicles"].sum()))

    st.markdown("---")

    # ========================
    # CHARTS
    # ========================
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📏 Distance Per Session")
        chart_data = analytics[["session_id", "total_distance"]].set_index("session_id")
        st.bar_chart(chart_data)

    with col2:
        st.subheader("📦 Demand Per Session")
        chart_data = analytics[["session_id", "total_demand"]].set_index("session_id")
        st.bar_chart(chart_data)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👥 Customers Per Session")
        chart_data = analytics[["session_id", "total_customers"]].set_index("session_id")
        st.bar_chart(chart_data)

    with col2:
        st.subheader("🚚 Vehicles Per Session")
        chart_data = analytics[["session_id", "total_vehicles"]].set_index("session_id")
        st.bar_chart(chart_data)

    st.markdown("---")

    # ========================
    # FULL TABLE
    # ========================
    st.subheader("📋 Full Analytics Table")
    display_df = analytics.copy()
    display_df["created_at"] = display_df["created_at"].astype(str).str[:19]
    display_df.columns = [
        "Session ID", "Date", "Customers", "Clusters",
        "Vehicle Capacity", "Total Clusters",
        "Total Distance (km)", "Total Demand", "Total Vehicles"
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
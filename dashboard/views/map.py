import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_all_sessions, get_session_routes, get_session_customers

API_URL = "http://127.0.0.1:8000"


def show():
    st.title("🗺️ Route Map Viewer")
    st.markdown("---")

    sessions = get_all_sessions()

    if sessions.empty:
        st.warning("No delivery sessions found. Run a delivery optimization first!")
        return

    # Session selector
    session_ids = sessions["id"].tolist()
    selected_session = st.selectbox(
        "Select Session to View",
        session_ids,
        format_func=lambda x: f"Session {x} — {str(sessions[sessions['id']==x]['created_at'].values[0])[:19]}"
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    # Session info
    session_row = sessions[sessions["id"] == selected_session].iloc[0]
    with col1:
        st.info(f"""
        **Session ID:** {selected_session}
        **Date:** {str(session_row['created_at'])[:19]}
        **Customers:** {session_row['total_customers']}
        **Clusters:** {session_row['num_clusters']}
        """)

    # Routes summary
    routes_df = get_session_routes(selected_session)
    with col2:
        if not routes_df.empty:
            st.info(f"""
            **Total Routes:** {len(routes_df)}
            **Total Distance:** {round(routes_df['distance_km'].sum(), 2)} km
            **Total Demand:** {round(routes_df['total_demand'].sum(), 2)} cans
            **Total Vehicles:** {int(routes_df['num_vehicles'].sum())}
            """)

    st.markdown("---")

    # Embed map
    st.subheader("🗺️ Delivery Map")
    st.caption("This shows the most recently generated map.")
    st.markdown(f"🔗 [Open map in full screen]({API_URL}/static/delivery_map.html)")

    st.components.v1.iframe(
        f"{API_URL}/static/delivery_map.html",
        height=500
    )

    st.markdown("---")

    # Routes table
    st.subheader("📋 Route Details")
    if not routes_df.empty:
        display_df = routes_df.copy()
        display_df.columns = [
            "Cluster", "Vehicle", "Route Stops",
            "Distance (km)", "Total Demand", "Num Vehicles"
        ]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
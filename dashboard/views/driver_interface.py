import streamlit as st
import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_URL = "http://127.0.0.1:8000"

# Available drivers
DRIVERS = ["D1", "D2", "D3"]


def show():
    st.title("🚚 Driver Interface")
    st.markdown("---")

    # ========================
    # DRIVER LOGIN
    # ========================
    st.subheader("👤 Driver Login")

    col1, col2 = st.columns([1, 2])
    with col1:
        driver_id = st.selectbox("Select Your Driver ID", DRIVERS)

    with col2:
        st.info(f"""
        **Driver:** {driver_id}
        **Status:** Active
        **Date:** Today
        """)

    st.markdown("---")

    if st.button("🔍 Load My Deliveries", type="primary"):
        with st.spinner("Loading your deliveries..."):
            try:
                response = requests.get(
                    f"{API_URL}/driver/{driver_id}/deliveries"
                )

                if response.status_code == 200:
                    result = response.json()

                    if "error" in result or not result.get("deliveries"):
                        st.warning("No pending deliveries found for today!")
                        st.info("Ask admin to run optimization first.")
                        return

                    deliveries = result["deliveries"]
                    session_id = result["session_id"]

                    # ========================
                    # PROGRESS BAR
                    # ========================
                    progress_response = requests.get(
                        f"{API_URL}/driver/{driver_id}/progress/{session_id}"
                    )

                    if progress_response.status_code == 200:
                        progress = progress_response.json()
                        total = progress["total"]
                        delivered = progress["delivered"]
                        pending = progress["pending"]

                        st.subheader("📊 Today's Progress")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Stops", total)
                        with col2:
                            st.metric("Delivered", delivered)
                        with col3:
                            st.metric("Pending", pending)

                        if total > 0:
                            st.progress(delivered / total)

                    st.markdown("---")

                    # ========================
                    # DELIVERY LIST
                    # ========================
                    st.subheader("📋 Pending Deliveries")

                    for delivery in deliveries:
                        with st.container():
                            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

                            with col1:
                                st.write(f"**{delivery['customer_id']}**")
                                name = delivery['customer_name'] or 'N/A'
                                st.caption(f"👤 {name}")

                            with col2:
                                st.write(f"📦 {delivery['num_cans']} cans")
                                st.caption(f"Cluster {delivery['cluster_id']}")

                            with col3:
                                status = delivery['status']
                                if status == "delivered":
                                    st.success("✅ Done")
                                else:
                                    st.warning("⏳ Pending")

                            with col4:
                                if delivery['status'] == "pending":
                                    if st.button(
                                        "Mark Done",
                                        key=f"deliver_{delivery['id']}"
                                    ):
                                        mark_response = requests.post(
                                            f"{API_URL}/driver/mark-delivered/{delivery['id']}"
                                        )
                                        if mark_response.status_code == 200:
                                            st.success("Marked as delivered!")
                                            st.rerun()

                            st.divider()

                    st.markdown("---")

                    # ========================
                    # ROUTE MAP
                    # ========================
                    st.subheader("🗺️ Your Route Map")
                    st.caption("Follow this route for delivery")
                    st.markdown(
                        f"[Open Full Map]({API_URL}/static/delivery_map.html)"
                    )
                    st.components.v1.iframe(
                        f"{API_URL}/static/delivery_map.html",
                        height=400
                    )

                else:
                    st.error(f"API Error: {response.status_code}")

            except Exception as e:
                st.error(f"Error: {str(e)}")
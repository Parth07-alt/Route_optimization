import streamlit as st
import sys
import os

# ✅ Add dashboard directory to Python path
dashboard_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, dashboard_dir)

st.set_page_config(
    page_title="Smart Water Distribution System",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("💧 Water Distribution")
st.sidebar.markdown("---")

# Add to radio options
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "📦 New Delivery", "🗺️ Route Map", 
     "📊 Analytics", "🚚 Driver Stats", "🚗 Driver Interface"]  # 🆕
)

# Add at bottom


st.sidebar.markdown("---")
st.sidebar.info("Smart Water Distribution Optimization System")

# ✅ Use importlib for reliable imports
import importlib.util

def load_view(filename):
    path = os.path.join(dashboard_dir, "views", filename)
    spec = importlib.util.spec_from_file_location("view", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

if page == "🏠 Home":
    load_view("home.py").show()

elif page == "📦 New Delivery":
    load_view("delivery.py").show()

elif page == "🗺️ Route Map":
    load_view("map.py").show()

elif page == "📊 Analytics":
    load_view("analytics.py").show()

elif page == "🚚 Driver Stats":
    load_view("driver_stats.py").show()

elif page == "🚗 Driver Interface":
    load_view("driver_interface.py").show()    
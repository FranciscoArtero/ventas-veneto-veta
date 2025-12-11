import streamlit as st
from src.services.postgres_service import init_db
from src.ui.dashboard import render_dashboard_page
from src.ui.products import render_products_page
from src.ui.ventas import render_ventas_page

# 1. Config Global
st.set_page_config(page_title="VENTAS VETA", page_icon="📦", layout="wide")

# CSS Injection for Branding (Grayscale Theme)
st.markdown("""
<style>
    /* 1. Sidebar Background & Text */
    [data-testid="stSidebar"] {
        background-color: #2C2C2C !important; /* Dark Gray Sidebar */
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div[role="radiogroup"] {
        color: #E0E0E0 !important; /* Light Gray Text */
    }
    
    /* 2. Main Area Background (Handled by config.toml, but explicit override just in case) */
    .stApp {
        background-color: #F4F4F4 !important; /* Very Light Gray */
    }

    /* 3. Input Widgets */
    /* Background Color for Inputs - Light Gray */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #E0E0E0 !important; 
        color: #262730 !important; /* Dark Text */
        border-color: #A0A0A0 !important; /* Medium Gray Border */
    }
    
    /* Text Color inside Inputs Selectbox */
    .stSelectbox div[data-baseweb="select"] span {
        color: #262730 !important;
    }
    
    /* Dropdown Menu Items */
    ul[data-baseweb="menu"] {
        background-color: #E0E0E0 !important;
    }
    ul[data-baseweb="menu"] li span {
        color: #262730 !important;
    }
    
    /* 4. Labels */
    /* Main Area labels */
    .main label {
        color: #262730 !important; /* Dark Text */
    }
    
    /* Sidebar labels */
    [data-testid="stSidebar"] label {
        color: #E0E0E0 !important;
    }
    
    /* Buttons */
    button[kind="primary"] {
        background-color: #606060 !important;
        border: none !important;
        color: white !important;
    }
    button[kind="secondary"] {
        background-color: #E0E0E0 !important;
        border: 1px solid #606060 !important;
        color: #262730 !important;
    }

</style>
""", unsafe_allow_html=True)


# 2. Init DB
init_db()

# 3. Sidebar Navigation
# Logo Injection
try:
    st.sidebar.image("assets/VETA_Wall_Panels_Logo.png", use_container_width=True)
except:
    st.sidebar.warning("Logo not found at assets/VETA_Wall_Panels_Logo.png")

# --- 2.1 CLEAN SIDEBAR ---
# Removed Global Brand Selector as per new requirements (Page-Level Control)
# Keeping only Navigation

page = st.sidebar.radio(
    "Navegación",
    ["Dashboard", "Nueva Venta", "Productos", "Clientes", "Concesión", "Facturación"],
    index=0
)

# NEW: Reset Button
from src.ui.state_manager import render_brand_reset_button_sidebar
render_brand_reset_button_sidebar()

st.sidebar.divider()
st.sidebar.caption("v2.4 - Consignment Module")

from src.ui.clientes import render_clientes_page
from src.ui.facturacion import render_facturacion_page
from src.ui.concesion import render_concesion_page

# 4. Routing
# Note: Functions now handle their own state/context or use defaults
if page == "Dashboard":
    render_dashboard_page()
elif page == "Nueva Venta":
    render_ventas_page()
elif page == "Productos":
    render_products_page()
elif page == "Clientes":
    render_clientes_page()
elif page == "Concesión":
    render_concesion_page()
elif page == "Facturación":
    render_facturacion_page()

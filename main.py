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

    /* --- MOBILE OPTIMIZATION --- */
    @media (max-width: 640px) {
        /* Reduce padding at the top of the main container */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Reduce Header sizes for mobile */
        h1 {
            font-size: 1.6rem !important;
        }
        h2 {
            font-size: 1.3rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        
        /* Adjust global font size if needed */
        p, div, label, span {
            font-size: 0.95rem !important;
        }
        
        /* Improve contrast and spacing for inputs on mobile */
        .stTextInput input, .stNumberInput input, .stSelectbox div {
             min-height: 45px !important;
        }
    }

    /* Refined Shadows and Contrast for Grayscale Theme */
    .stApp {
        background-color: #F8F9FA !important; /* Slightly brighter than F4F4F4 for better contrast */
    }
    
    /* Card-like effect for containers if users use them, or metric cards */
    [data-testid="stMetricValue"] {
        color: #2C2C2C !important;
    }

    /* --- HIDE STREAMLIT UI (Developer Options) --- */
    /* Ocultar el menú superior (Github, Share, 3 Puntos, etc.) */
    menu button[data-testid="stActionButtonIcon"], 
    header {
        visibility: hidden;
    }

    /* Ocultar el pie de página (Made with Streamlit/logos) */
    footer {
        visibility: hidden;
    }

    /* Asegurar que el contenido no se rompa */
    .stApp > header {
        display: none;
    }
    
</style>
""", unsafe_allow_html=True)


# 2. Init DB
init_db()

# 3. Sidebar Navigation
# Logo Injection
try:
    st.sidebar.image("assets/nuevo_logo_veta.png", use_container_width=True)
except:
    st.sidebar.warning("Logo not found at assets/nuevo_logo_veta.png")

# --- 2.1 CLEAN SIDEBAR ---
# Navigate Logic

page = st.sidebar.radio(
    "Navegación",
    ["Dashboard", "Nueva Venta", "Productos", "Clientes", "Concesión", "Facturación"],
    index=0
)

# --- 3.1 MOBILE SIDEBAR AUTO-CLOSE LOGIC ---
import streamlit.components.v1 as components
# Inject JS to detect click on sidebar radio inputs and close sidebar if on mobile
components.html("""
<script>
    document.addEventListener('DOMContentLoaded', function() {
        function addMobileHandler() {
            const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
            if (!sidebar) return;
            
            // Find all radio options in the sidebar
            // Note: Targeting the labels usually works best as they capture the click
            const radioLabels = window.parent.document.querySelectorAll('[data-testid="stSidebar"] [data-testid="stRadio"] label');
            
            radioLabels.forEach(label => {
                label.addEventListener('click', function() {
                    // Check if mobile (width < 640px)
                    if (window.parent.innerWidth <= 640) {
                        // Find the close button (often X or chevron in sidebar)
                        // Streamlit's sidebar close btn usually has specific aria-label or testid
                        const closeBtn = window.parent.document.querySelector('[data-testid="stSidebar"] button');
                        if (closeBtn) {
                            setTimeout(() => {
                                closeBtn.click();
                            }, 150); // Short delay to ensure selection registers
                        }
                    }
                });
            });
        }
        
        // Attempt to attach on load and after small delay to ensure elements render
        addMobileHandler();
        setTimeout(addMobileHandler, 500);
        setTimeout(addMobileHandler, 1000);
    });
</script>
""", height=0, width=0)

# NEW: Reset Button
from src.ui.state_manager import render_brand_reset_button_sidebar
render_brand_reset_button_sidebar()

st.sidebar.divider()
st.sidebar.caption("v2.5 - Mobile Optimized")

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

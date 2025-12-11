import streamlit as st
import pandas as pd
from datetime import datetime
from src.services.postgres_service import leer_ventas, leer_ventas_items, leer_stock
from src.services.reports import get_kpis, get_top_products, get_revenue_trend, get_top_clients
from src.config import TIMEZONE

# from src.ui.state_manager import require_brand_selection # Not used here, this is Consolidated

def render_dashboard_page():
    st.title("📊 Tablero de Control (Consolidado)")

    # --- FILTERS SECTION ---
    # Global Filters for Reporting: Year, Month, Brand (default Ambas)
    
    col_filters = st.columns(3)
    
    # Year Filter
    current_year = datetime.now().year
    sel_year = col_filters[0].selectbox("Año", [current_year, current_year-1, current_year-2], index=0)
    
    # Month Filter
    months_map = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    current_month = datetime.now().month
    sel_month_name = col_filters[1].selectbox("Mes", options=list(months_map.values()), index=current_month - 1)
    sel_month = [k for k,v in months_map.items() if v == sel_month_name][0]
    
    # Marca Filter
    marca_opciones = ["Ambas Marcas", "VETA", "VENETO"]
    sel_marca_label = col_filters[2].selectbox("Marca", options=marca_opciones, index=0)
    
    # Determine 'marca' arg for service
    marca_arg = None if sel_marca_label == "Ambas Marcas" else sel_marca_label

    # --- LOAD DATA ---
    try:
        ventas = leer_ventas(marca_arg)
        # items = leer_ventas_items(marca_arg) # Optional if needed for deeper analytics
        items_all = leer_ventas_items(marca_arg)
        stock = leer_stock(marca_arg)
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return

    # --- PROCESS MTD / YTD with Python Filtering ---
    # Service returns ALL history for that brand (or all brands).
    # We interpret 'reference_date' for MTD.
    reference_date = datetime(sel_year, sel_month, 1)
    
    # KPIS
    kpis = get_kpis(stock, ventas, reference_date)
    
    st.divider()
    
    # Metrics Row
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"Ventas {sel_month_name}", f"${kpis['mtd_neto']:,.0f}")
    k2.metric(f"Ventas {sel_year}", f"${kpis['ytd_neto']:,.0f}")
    k3.metric("Transacciones (Mes)", kpis['total_transacciones'])
    k4.metric("Stock Crítico", kpis['stock_critico'], delta_color="inverse")
    
    st.divider()

    # --- CHARTS ---
    # Filter for Charts: Match Year AND Month
    filtered_ventas = [v for v in ventas if v.fecha.year == sel_year and v.fecha.month == sel_month]
    filtered_ids = {v.id for v in filtered_ventas}
    filtered_items = [i for i in items_all if i.venta_id in filtered_ids]

    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📈 Evolución Diaria")
        if filtered_ventas:
            trend_df = get_revenue_trend(filtered_ventas)
            st.line_chart(trend_df.set_index('fecha'), color="#21c354")
        else:
            st.caption("Sin datos para este mes.")

    with c2:
        st.subheader("🏆 Top Productos")
        if filtered_items:
            # We need stock for names. Logic in get_top_products handles mapping.
            top_prod = get_top_products(filtered_items, stock)
            st.bar_chart(top_prod.set_index('nombre_producto'), color="#ff4b4b")
        else:
            st.caption("Sin datos para este mes.")

    # Top Clients
    st.subheader("💎 Mejores Clientes")
    if filtered_ventas:
        top_clients = get_top_clients(filtered_ventas)
        st.dataframe(top_clients.style.format({"total_neto": "${:,.0f}"}), use_container_width=True)
    else:
        st.info("No hay actividad de clientes este mes.")

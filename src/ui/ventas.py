import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict
from src.services.postgres_service import leer_stock, registrar_venta
from src.models import StockItem, Venta, VentaItem
from src.config import TZ_AR

def init_venta_state():
    if "cart" not in st.session_state:
        st.session_state.cart = [] # List of dicts or VentaItems
    if "client_name" not in st.session_state:
        st.session_state.client_name = ""

from src.ui.state_manager import require_brand_selection

def render_ventas_page():
    # --- BRAND SELECTION BARRIER ---
    marca = require_brand_selection()
    if not marca:
        return

    init_venta_state()
    st.title(f"Nueva Venta 🛒 ({marca})")

    from src.services.cliente_service import leer_clientes, crear_cliente
    from src.models import Cliente
    
    # --- STEP 2: LOAD DATA & CONTEXT (Now Main Step) ---

    # ---------------------------------------------------------
    # 1. CLIENTE INFO (Selector + Quick Add)
    # ---------------------------------------------------------
    
    # Refresh logic helper
    if 'sales_force_refresh_clients' not in st.session_state:
        st.session_state.sales_force_refresh_clients = False

    # Load Clients
    try:
        clientes_list = leer_clientes(marca)
    except:
        clientes_list = []
        
    client_options = {c.razon_social: c for c in clientes_list}
    client_names = list(client_options.keys())

    # Layout: Selector (Large) | Add Button (Small)
    c_sel, c_add = st.columns([3, 1])
    
    # We use session state to hold the selected value if we want to auto-select new one
    # If adding new, we set index to the new one.
    
    # Selector
    selected_name = c_sel.selectbox(
        "Cliente", 
        options=client_names, 
        index=client_names.index(st.session_state.client_name) if st.session_state.client_name in client_names else 0,
        placeholder="Seleccione un cliente...",
        key="sb_client_selector"
    )
    
    # Update state
    if selected_name:
        st.session_state.client_name = selected_name

    # Quick Add Button
    if c_add.button("➕ Cliente", help="Crear nuevo cliente"):
        st.session_state.show_quick_client_form = not st.session_state.get('show_quick_client_form', False)

    # Quick Add Form (Expander/Container)
    if st.session_state.get('show_quick_client_form', False):
        with st.container():
            st.info(f"Nuevo Cliente Rápido en {marca}")
            qc1, qc2, qc3 = st.columns([2, 2, 1])
            q_razon = qc1.text_input("Razón Social", key="q_razon")
            q_cuit = qc2.text_input("CUIT", key="q_cuit")
            
            if qc3.button("Guardar", type="primary"):
                if q_razon:
                    try:
                        ne = Cliente(id=0, razon_social=q_razon, cuit_cuil=q_cuit, marca=marca)
                        crear_cliente(ne)
                        st.success(f"Creado: {q_razon}")
                        st.session_state.client_name = q_razon # Auto select
                        st.session_state.show_quick_client_form = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")
                else:
                    st.error("Falta Razón Social")
    st.divider()

    # ---------------------------------------------------------
    # 2. SELECCION DE PRODUCTOS
    # ---------------------------------------------------------
    st.subheader("Agregar Productos")
    
    # Load Stock
    try:
        stock_items = leer_stock(marca)
    except Exception as e:
        stock_items = []
        st.error(f"Error cargando stock: {e}")

    if stock_items:
        # Prepare options: "Nombre (Stock: X)"
        # Map label -> item object
        item_map = {f"{i.nombre} (Stock: {i.cantidad})": i for i in stock_items}
        
        c1, c2, c3 = st.columns([3, 1, 1])
        
        selected_label = c1.selectbox("Seleccionar Producto", options=list(item_map.keys()))
        selected_item: StockItem = item_map[selected_label]
        
        # Determine max logic (if strict limit needed, but requirement said negative allowed, just warning)
        qty_input = c2.number_input("Cantidad", min_value=1, value=1, step=1)
        
        # Add Button
        if c3.button("Agregar +"):
            # Check if warning needed
            if qty_input > selected_item.cantidad:
                st.warning(f"⚠️ Cantidad solicitada ({qty_input}) supera stock actual ({selected_item.cantidad}).")
            
            # Create Cart Item
            subtotal = qty_input * selected_item.precio_unitario
            cart_item = {
                "producto_id": selected_item.id,
                "nombre": selected_item.nombre, # modelo_placa
                "cantidad": qty_input,
                "precio_unitario": selected_item.precio_unitario,
                "subtotal": subtotal,
                "stock_actual": selected_item.cantidad # for reference
            }
            st.session_state.cart.append(cart_item)
            st.success(f"{selected_item.nombre} agregado.")

    # ---------------------------------------------------------
    # 3. CARRITO & TOTALES
    # ---------------------------------------------------------
    st.divider()
    st.subheader("Detalle de Venta")
    
    if st.session_state.cart:
        # Display Cart
        cart_df = pd.DataFrame(st.session_state.cart)
        # Rename cols for display
        display_df = cart_df[["nombre", "cantidad", "precio_unitario", "subtotal", "stock_actual"]]
        
        # Highlight logic if stock issue
        def highlight_stock_warning(row):
            if row['cantidad'] > row['stock_actual']:
                return ['background-color: #ffeeba'] * len(row)
            return [''] * len(row)
            
        st.dataframe(
            display_df.style.apply(highlight_stock_warning, axis=1),
            use_container_width=True,
             column_config={
                "precio_unitario": st.column_config.NumberColumn(format="$%.2f"),
                "subtotal": st.column_config.NumberColumn(format="$%.2f")
            }
        )
        
        # Remove Item?
        if st.button("Limpiar Carrito"):
            st.session_state.cart = []
            st.rerun()
            
        # Financials
        total_bruto = sum(item["subtotal"] for item in st.session_state.cart)
        
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        c_fin1.metric("Total Bruto", f"${total_bruto:,.2f}")
        
        discount_pct = c_fin2.number_input("Descuento (%)", min_value=0.0, max_value=100.0, step=0.5, value=0.0)
        
        discount_amount = total_bruto * (discount_pct / 100)
        total_neto = total_bruto - discount_amount
        
        c_fin3.metric("Total a Pagar", f"${total_neto:,.2f}", delta=f"-${discount_amount:,.2f}" if discount_amount > 0 else None)

        # ---------------------------------------------------------
        # 4. CONFIRMACION
        # ---------------------------------------------------------
        st.markdown("###")
        if st.button("✅ CONFIRMAR VENTA", type="primary", use_container_width=True):
            if not st.session_state.client_name:
                st.error("Por favor ingresa el nombre del Cliente.")
            else:
                # Build Objects
                venta_obj = Venta(
                    id=0, # Auto-generated
                    fecha=datetime.now(TZ_AR),
                    cliente=st.session_state.client_name,
                    total_bruto=total_bruto,
                    descuento_porcentaje=discount_pct,
                    total_neto=total_neto,
                    estado="confirmada",
                    marca=marca
                )
                
                items_objs = []
                for c in st.session_state.cart:
                    item_obj = VentaItem(
                        id=0,
                        venta_id=0,
                        producto_id=c["producto_id"],
                        cantidad=c["cantidad"],
                        precio_unitario=c["precio_unitario"],
                        subtotal=c["subtotal"],
                        marca=marca
                    )
                    items_objs.append(item_obj)
                
                try:
                    with st.spinner("Procesando transacción..."):
                        new_id = registrar_venta(venta_obj, items_objs)
                    
                    st.success(f"Venta #{new_id} registrada correctamente!")
                    
                    # Reset State
                    st.session_state.cart = []
                    st.session_state.client_name = ""
                    # st.experimental_rerun() # Optional
                    
                except Exception as e:
                    st.error(f"Error procesando venta: {e}")
    else:
        st.info("El carrito está vacío.")

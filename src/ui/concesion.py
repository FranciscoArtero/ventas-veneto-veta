import streamlit as st
import pandas as pd
from datetime import datetime
from src.ui.state_manager import require_brand_selection
from src.services.concesion_service import (
    get_concesionarios, crear_concesionario, registrar_salida_concesion, 
    leer_stock_concesion, confirmar_venta_concesion, eliminar_concesionario, actualizar_concesionario
)
from src.services.postgres_service import leer_stock

def delete_socio_handler(sid):
    try:
        eliminar_concesionario(sid)
        st.toast("Socio eliminado")
    except ValueError as ve:
        st.error(str(ve))

def render_concesion_page():
    # --- BRAND SELECTION BARRIER ---
    marca = require_brand_selection()
    if not marca:
        return

    st.title(f"🤝 Gestión de Concesión ({marca})")
    
    tab1, tab2, tab3 = st.tabs(["Gestión de Socios", "Registro de Salida (Stock)", "Reporte de Ventas (Stock en Consignación)"])

    # --- TAB 1: SOCIOS ---
    with tab1:
        st.header("Socios / Concesionarios")
        
        # Initialize State for Forms
        if 'new_socio_name' not in st.session_state: st.session_state.new_socio_name = ""
        if 'new_socio_cuit' not in st.session_state: st.session_state.new_socio_cuit = ""
        if 'new_socio_contact' not in st.session_state: st.session_state.new_socio_contact = ""
        if 'editing_socio_id' not in st.session_state: st.session_state.editing_socio_id = None

        # Helper to clear form
        def clear_socio_form():
            st.session_state.new_socio_name = ""
            st.session_state.new_socio_cuit = ""
            st.session_state.new_socio_contact = ""

        # List Existing
        socios = get_concesionarios(marca)
        
        with st.expander("➕ Nuevo Socio", expanded=False):
            with st.form("new_socio_form", clear_on_submit=False): # We handle clear manually to match requirement
                c1, c2 = st.columns(2)
                name_val = c1.text_input("Nombre / Razón Social", key="new_socio_name")
                cuit_val = c2.text_input("CUIT / CUIL", key="new_socio_cuit")
                cont_val = st.text_input("Contacto", key="new_socio_contact")
                
                submitted = st.form_submit_button("Crear Socio")
                if submitted:
                    if name_val:
                        try:
                            crear_concesionario(name_val, cuit_val, cont_val, marca)
                            st.success("Socio creado exitosamente.")
                            clear_socio_form()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("El nombre es obligatorio.")

        if socios:
            st.divider()
            # Custom Header Layout
            # Widths: ID (0.5), Name (2), CUIT (1.5), Contact (1.5), Actions (1)
            h_cols = st.columns([0.5, 2, 1.5, 1.5, 1]) 
            h_cols[0].markdown("**ID**")
            h_cols[1].markdown("**Nombre / Empresa**")
            h_cols[2].markdown("**CUIT / CUIL**")
            h_cols[3].markdown("**Contacto**")
            h_cols[4].markdown("**Acciones**")
            st.divider()
            
            for s in socios:
                # EDIT MODE check
                if st.session_state.editing_socio_id == s.id:
                     with st.form(f"edit_socio_{s.id}"):
                        ce1, ce2 = st.columns(2)
                        e_name = ce1.text_input("Nombre", value=s.nombre_socio)
                        e_cuit = ce2.text_input("CUIT/CUIL", value=s.cuit_cuil if s.cuit_cuil else "")
                        e_cont = st.text_input("Contacto", value=s.contacto if s.contacto else "")
                        
                        b1, b2 = st.columns([1,1])
                        if b1.form_submit_button("💾 Guardar"):
                            from src.services.concesion_service import actualizar_concesionario
                            actualizar_concesionario(s.id, e_name, e_cuit, e_cont)
                            st.session_state.editing_socio_id = None
                            st.rerun()
                        if b2.form_submit_button("❌ Cancelar"):
                            st.session_state.editing_socio_id = None
                            st.rerun()
                else:
                    # VIEW MODE
                    cols = st.columns([0.5, 2, 1.5, 1.5, 1])
                    cols[0].write(f"#{s.id}")
                    cols[1].markdown(f"**{s.nombre_socio}**")
                    cols[2].write(s.cuit_cuil if s.cuit_cuil else "-")
                    cols[3].write(s.contacto if s.contacto else "-")
                    
                    # Actions
                    ac1, ac2 = cols[4].columns(2)
                    if ac1.button("✏️", key=f"e_s_{s.id}"):
                        st.session_state.editing_socio_id = s.id
                        st.rerun()
                    if ac2.button("🗑️", key=f"d_s_{s.id}"):
                        st.warning(f"¿Eliminar socio {s.nombre_socio}?")
                        st.button("Sí, Eliminar", key=f"conf_del_s_{s.id}", on_click=delete_socio_handler, args=(s.id,))

        else:
            st.info("No hay socios registrados para esta marca.")
            st.info("No hay socios registrados para esta marca.")

    # --- TAB 2: REGISTRO DE SALIDA ---
    with tab2:
        st.header("Enviar Stock a Concesión")
        
        if not socios:
            st.warning("Primero debe crear socios en la pestaña 'Gestión de Socios'.")
        else:
            # 1. Select Socio
            socio_opts = {s.nombre_socio: s.id for s in socios}
            sel_socio_name = st.selectbox("Seleccionar Socio", list(socio_opts.keys()))
            sel_socio_id = socio_opts[sel_socio_name]
            
            # 2. Add Items to "Cart" for Transfer
            if 'concesion_cart' not in st.session_state:
                st.session_state.concesion_cart = []

            # Load Main Stock for Selection
            stock_main = leer_stock(marca)
            stock_map = {p.nombre: p for p in stock_main if p.cantidad > 0}
            
            c1, c2, c3 = st.columns([3, 1, 1])
            if stock_map:
                sel_prod_name = c1.selectbox("Producto de Depósito", list(stock_map.keys()))
                sel_prod = stock_map[sel_prod_name]
                sel_qty = c2.number_input("Cantidad", min_value=1, max_value=sel_prod.cantidad, value=1)
                
                if c3.button("Agregar"):
                    # Add to cart list
                    st.session_state.concesion_cart.append({
                        "producto_id": sel_prod.id,
                        "nombre": sel_prod.nombre,
                        "cantidad": sel_qty
                    })
            else:
                st.warning("No hay stock disponible en depósito para enviar.")

            # Show Cart
            if st.session_state.concesion_cart:
                st.write("##### Items a Enviar:")
                cart_df = pd.DataFrame(st.session_state.concesion_cart)
                st.dataframe(cart_df)
                
                if st.button("Confirmar Envío de Mercadería", type="primary"):
                    try:
                        registrar_salida_concesion(sel_socio_id, marca, st.session_state.concesion_cart)
                        st.success(f"Stock enviado exitosamente a {sel_socio_name}")
                        st.session_state.concesion_cart = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en el envío: {e}")
                
                if st.button("Limpiar Lista"):
                    st.session_state.concesion_cart = []
                    st.rerun()

    # --- TAB 3: REPORTE DE VENTAS (Y CONFIRMACIÓN) ---
    with tab3:
        st.header("Stock en Consignación y Ventas")
        
        # Strategy: Show list of dealers, select one to view their stock and manage sales
        if not socios:
            st.info("Sin socios.")
        else:
            socio_opts_t3 = {s.nombre_socio: s.id for s in socios}
            # Optional: Allow viewing all? For now, per dealer is safer for specific actions
            sel_socio_report_name = st.selectbox("Ver Stock de:", list(socio_opts_t3.keys()), key="sel_socio_t3")
            sel_socio_report_id = socio_opts_t3[sel_socio_report_name]
            
            stock_conc = leer_stock_concesion(sel_socio_report_id)
            
            if not stock_conc:
                st.info(f"{sel_socio_report_name} no tiene stock en consignación activo.")
            else:
                st.write(f"Inventario actual en **{sel_socio_report_name}**:")
                
                # HEADER
                header_cols = st.columns([3, 1, 2])
                header_cols[0].markdown("**Producto**")
                header_cols[1].markdown("**Disp.**")
                header_cols[2].markdown("**Cant. a Procesar**")
                st.divider()
                
                # Collect item IDs and their input keys
                process_data = {} # {id: key}
                
                with st.form("bulk_actions_form", clear_on_submit=True):
                    for item in stock_conc:
                        c1, c2, c3 = st.columns([3, 1, 2])
                        c1.write(f"{item['producto_nombre']} ({item['producto_codigo']})")
                        c2.markdown(f"**{item['cantidad_disponible']}**")
                        
                        # Input for Quantity
                        k = f"proc_qty_{item['id']}"
                        c3.number_input(
                            "Qty", 
                            min_value=0.0, 
                            max_value=float(item['cantidad_disponible']), 
                            step=1.0, 
                            key=k,
                            label_visibility="collapsed"
                        )
                        process_data[item['id']] = {'key': k, 'prod_id': item['producto_id']}
                    
                    st.divider()
                    
                    # Global Actions
                    b1, b2 = st.columns(2)
                    
                    # --- BULK SELL ---
                    # Note: We check session_state directly because usually form widgets update state on submit
                    if b1.form_submit_button("💸 Confirmar Venta", type="primary"):
                        items_to_sell = []
                        for row_id, data in process_data.items():
                            qty = st.session_state.get(data['key'], 0.0)
                            if qty > 0:
                                items_to_sell.append({'producto_id': data['prod_id'], 'cantidad': qty})
                        
                        if not items_to_sell:
                            st.warning("No has seleccionado cantidades para vender.")
                        else:
                            try:
                                confirmar_venta_concesion(sel_socio_report_id, marca, items_to_sell)
                                st.success(f"Venta masiva registrada ({len(items_to_sell)} productos).")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error en venta: {e}")

                    # --- BULK RETURN ---
                    if b2.form_submit_button("↩️ Devolver Stock"):
                        items_to_ret = []
                        for row_id, data in process_data.items():
                            qty = st.session_state.get(data['key'], 0.0)
                            if qty > 0:
                                items_to_ret.append({'producto_id': data['prod_id'], 'cantidad': qty})
                                
                        if not items_to_ret:
                            st.warning("No has seleccionado cantidades para devolver.")
                        else:
                            try:
                                from src.services.concesion_service import devolver_stock_concesion_masivo
                                devolver_stock_concesion_masivo(sel_socio_report_id, items_to_ret)
                                st.success(f"Devolución masiva registrada ({len(items_to_ret)} productos).")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error en devolución: {e}")

from src.services.concesion_service import get_concesionarios
import streamlit as st
import pandas as pd
from src.services.postgres_service import (
    leer_ventas, leer_items_por_venta, actualizar_estado_facturacion, leer_stock,
    eliminar_venta, actualizar_cantidad_item_venta, actualizar_descuento_venta
)
from src.services.cliente_service import leer_clientes
from src.config import IVA_RATE
from src.models import Venta

from datetime import datetime

def render_facturacion_page():
    st.title("🧾 Facturación (Consolidada)")

    # --- FILTERS SECTION ---
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
    
    # Arg for service
    marca_arg = None if sel_marca_label == "Ambas Marcas" else sel_marca_label

    try:
        # Load Data
        ventas_raw = leer_ventas(marca=marca_arg)
        # Filter by Date
        ventas = [v for v in ventas_raw if v.fecha.year == sel_year and v.fecha.month == sel_month]
        
        # Load Clientes
        clientes = leer_clientes(marca=None)
        
        # Load Concesionarios (Handle Both Brands if needed)
        concesionarios = []
        if marca_arg:
            concesionarios = get_concesionarios(marca_arg)
        else:
            concesionarios = get_concesionarios("VETA") + get_concesionarios("VENETO")

        stock_items = leer_stock(marca=None)
        
        # Maps
        client_cuit_map = {c.razon_social: c.cuit_cuil for c in clientes}
        client_cuit_map_norm = {c.razon_social.strip().lower(): c.cuit_cuil for c in clientes}
        
        # Concesionario Map
        conc_cuit_map = {c.nombre_socio: c.cuit_cuil for c in concesionarios}
        conc_cuit_map_norm = {c.nombre_socio.strip().lower(): c.cuit_cuil for c in concesionarios}
        
        product_map = {p.id: p for p in stock_items}
        
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return

    if not ventas:
        st.info("No hay ventas registradas.")
        return
    
    # Kpi Summary
    total_pendientes = len([v for v in ventas if v.estado_facturacion == "No Facturado"])
    st.metric("Ventas Pendientes de Facturar (Global)", total_pendientes)
    
    st.divider()

    # --- TABLE HEADER ---
    # Layout: Check | ID | Marca | Fecha | Cliente | CUIT | Neto | Final | Estado | Acciones
    c_layout = [0.4, 0.5, 0.8, 0.8, 1.5, 1.0, 1.0, 1.0, 1.0, 0.8]
    
    h_cols = st.columns(c_layout)
    h_cols[1].markdown("**ID**")
    h_cols[2].markdown("**Marca**")
    h_cols[3].markdown("**Fecha**")
    h_cols[4].markdown("**Cliente**")
    h_cols[5].markdown("**CUIT/CUIL**")
    h_cols[6].markdown("**Valor Neto**")
    h_cols[7].markdown("**Valor Final**")
    h_cols[8].markdown("**Estado**")
    h_cols[9].markdown("**Editar**")
    st.divider()

    # Init Edit State
    if 'editing_factura_id' not in st.session_state:
        st.session_state.editing_factura_id = None

    # Iterate Sales
    for venta in ventas:
        # EDIT MODE RENDER
        if st.session_state.editing_factura_id == venta.id:
            with st.container():
                st.markdown(f"#### ✏️ Editando Venta #{venta.id}")
                st.info("Modifica los valores y guarda los cambios. 'Cancelar' para salir.")
                
                # Discount
                c_disc, c_save_disc = st.columns([2, 1])
                new_disc = c_disc.number_input("Descuento %", value=float(venta.descuento_porcentaje), step=1.0, key=f"ed_disc_{venta.id}")
                
                # Items
                items = leer_items_por_venta(venta.id)
                if items:
                    st.markdown("##### Items")
                    for it in items:
                        prod = product_map.get(it.producto_id)
                        p_name = prod.nombre if prod else f"ID {it.producto_id}"
                        
                        ci1, ci2, ci3 = st.columns([3, 1, 1])
                        ci1.write(f"**{p_name}**")
                        ci2.number_input("Cant", value=int(it.cantidad), min_value=1, step=1, key=f"ed_qty_{it.id}")
                        
                        # Apply Item Update Button per row or global? 
                        # To keep it simple based on previous backend, let's auto-save or per-row. 
                        # User wants "modificar". Let's use a "Guardar Todo" approach? 
                        # Backend `actualizar_cantidad` is atomic. 
                        # Let's Stick to per-item save for safety/simplicity with existing backend, 
                        # OR simple Save Button that calls item updates.
                        # For now -> Per row save is safest with current `sqlite_service`.
                        
                        if ci3.button("💾", key=f"save_it_{it.id}"):
                            q_val = st.session_state[f"ed_qty_{it.id}"]
                            actualizar_cantidad_item_venta(venta.id, it.id, q_val)
                            st.toast("Item actualizado")
                            # Don't rerun immediately to allow other edits? Or rerun to reflect totals?
                            # Rerun needed for totals.
                            st.rerun()

                st.divider()
                
                # Footer Actions
                fb1, fb2, fb3 = st.columns([1,1,1])
                if fb1.button("💾 Guardar Descuento", key=f"save_d_{venta.id}"):
                    actualizar_descuento_venta(venta.id, new_disc)
                    st.success("Descuento guardado.")
                    st.session_state.editing_factura_id = None
                    st.rerun()
                    
                if fb2.button("❌ Cerrar Edición", key=f"close_{venta.id}"):
                    st.session_state.editing_factura_id = None
                    st.rerun()

            st.divider()

        else:
            # NORMAL VIEW
            final_con_iva = venta.total_neto
            monto_neto_sin_iva = final_con_iva / (1 + IVA_RATE)
            
            # Get CUIT Logic
            c_key = venta.cliente
            cuit_val = client_cuit_map.get(c_key)
            if not cuit_val:
                cuit_val = client_cuit_map_norm.get(c_key.strip().lower(), "")
            if not cuit_val and " (Concesión)" in c_key:
                clean_name = c_key.replace(" (Concesión)", "").strip()
                cuit_val = conc_cuit_map.get(clean_name)
                if not cuit_val:
                    cuit_val = conc_cuit_map_norm.get(clean_name.lower(), "")
                
            with st.container():
                cols = st.columns(c_layout)
                
                # Checkbox
                is_facturado = (venta.estado_facturacion == "Facturado")
                def toggle_state(vid=venta.id, current=is_facturado):
                    new_val = "No Facturado" if current else "Facturado"
                    actualizar_estado_facturacion(vid, new_val)

                new_check = cols[0].checkbox("", value=is_facturado, key=f"chk_fac_{venta.id}", on_change=toggle_state)
                
                cols[1].write(f"#{venta.id}")
                marca_color = "blue" if venta.marca == "VETA" else "orange"
                cols[2].markdown(f":{marca_color}[**{venta.marca}**]")
                cols[3].write(venta.fecha.strftime("%d/%m/%Y"))
                cols[4].write(f"**{venta.cliente}**")
                cols[5].write(cuit_val if cuit_val else "-")
                cols[6].write(f"${monto_neto_sin_iva:,.2f}")
                cols[7].write(f"**${final_con_iva:,.2f}**")
                
                status_color = "green" if new_check else "red"
                status_text = "FACTURADO" if new_check else "PENDIENTE"
                cols[8].markdown(f":{status_color}[{status_text}]")
                
                # ACTIONS
                ac1, ac2 = cols[9].columns([1, 1])
                ac1.button("✏️", key=f"edt_btn_{venta.id}", help="Modificar Venta", on_click=lambda id=venta.id: setattr(st.session_state, 'editing_factura_id', id))
                
                if ac2.button("🗑️", key=f"del_btn_{venta.id}", help="Eliminar Venta"):
                    st.warning("¿Borrar?")
                    st.button("✅", key=f"conf_del_v_{venta.id}", on_click=eliminar_venta_handler, args=(venta.id,), help="Confirmar Eliminación")

                # Drill Down (Read Only)
                with st.expander(f"Ver Detalle #{venta.id}"):
                    items = leer_items_por_venta(venta.id)
                    if items:
                        detail_data = []
                        for it in items:
                            discount_multiplier = 1 - (venta.descuento_porcentaje / 100)
                            real_unit_price_final = it.precio_unitario * discount_multiplier
                            unit_neto = real_unit_price_final / (1 + IVA_RATE)
                            subtotal_final = real_unit_price_final * it.cantidad
                            subtotal_neto = subtotal_final / (1 + IVA_RATE)
                            
                            prod = product_map.get(it.producto_id)
                            p_code = prod.codigo if prod else "-"
                            p_name = prod.nombre if prod else f"ID {it.producto_id}"
                            
                            detail_data.append({
                                "Código": p_code,
                                "Producto": p_name,
                                "Cant": it.cantidad,
                                "Unit. Neto (S/IVA)": f"${unit_neto:,.2f}",
                                "Unit. Final (C/IVA)": f"${real_unit_price_final:,.2f}",
                                "Subt. Neto": f"${subtotal_neto:,.2f}",
                                "Subt. Final": f"${subtotal_final:,.2f}"
                            })
                        st.dataframe(pd.DataFrame(detail_data), use_container_width=True)
                    else:
                        st.warning("Sin items.")
            st.divider()

def eliminar_venta_handler(vid):
    eliminar_venta(vid)
    st.toast("Venta eliminada correctament.")

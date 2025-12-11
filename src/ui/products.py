import streamlit as st
import pandas as pd
from typing import List, Optional
from src.services.postgres_service import leer_stock, crear_producto, actualizar_producto, eliminar_producto
from src.models import StockItem

from src.ui.state_manager import require_brand_selection

def render_products_page():
    # --- BRAND SELECTION BARRIER ---
    marca = require_brand_selection()
    if not marca:
        return

    st.title(f"📦 Gestión de Productos ({marca})")

    # --- STATE MANAGEMENT ---
    # To handle "Edit Mode" for a specific item
    if 'editing_product_id' not in st.session_state:
        st.session_state.editing_product_id = None
    if 'show_create_form' not in st.session_state:
        st.session_state.show_create_form = False

    # --- 1. TOOLBAR (Create Button) ---
    col_tools, _ = st.columns([1, 4])
    if col_tools.button("➕ Nuevo Producto", type="primary", use_container_width=True):
        st.session_state.show_create_form = not st.session_state.show_create_form

    # --- 2. CREATE FORM (Collapsible) ---
    if st.session_state.show_create_form:
        with st.container():
            st.markdown(f"### ✨ Alta de Producto en {marca}")
            with st.form("create_product_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                new_codigo = c1.text_input("Código", help="Ej: 02")
                new_nombre = c2.text_input("Nombre / Modelo")
                new_categoria = c3.text_input("Categoría")
                
                c4, c5, c6 = st.columns(3)
                new_cantidad = c4.number_input("Cantidad", min_value=0, step=1)
                new_precio = c5.number_input("Precio ($)", min_value=0.0, step=100.0)
                new_min_stock = c6.number_input("Min. Stock", value=5, step=1)

                if st.form_submit_button("Guardar"):
                    try:
                        # Auto-validation
                        if not new_nombre:
                            st.error("El nombre es obligatorio.")
                        else:
                            item = StockItem(
                                id=0, 
                                codigo=new_codigo, 
                                nombre=new_nombre, 
                                categoria=new_categoria, 
                                cantidad=new_cantidad, 
                                precio_unitario=new_precio, 
                                min_stock=new_min_stock,
                                marca=marca
                            )
                            crear_producto(item)
                            st.success(f"Producto creado en {marca}!")
                            st.session_state.show_create_form = False
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            st.divider()

    # --- 3. PRODUCTS LIST & ACTIONS ---
    
    # Load Data
    try:
        items = leer_stock(marca)
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        items = []

    if not items:
        st.info(f"No hay productos registrados en {marca}.")
        return

    # Table Header
    # Using columns to create a "Grid" layout
    # Layout: ID | Cod | Nombre | Cantidad (Badge) | Precio | Acciones
    header_cols = st.columns([0.5, 0.5, 2, 1, 1, 1])
    header_cols[0].markdown("**ID**")
    header_cols[1].markdown("**Cód**")
    header_cols[2].markdown("**Producto**")
    header_cols[3].markdown("**Stock**")
    header_cols[4].markdown("**Precio**")
    header_cols[5].markdown("**Acciones**")
    st.divider()

    for item in items:
        # Check if we are editing THIS item
        if st.session_state.editing_product_id == item.id:
            # --- EDIT MODE ROW ---
            with st.container():
                with st.form(f"edit_form_{item.id}"):
                    ce1, ce2, ce3, ce4, ce5 = st.columns([1, 2, 1, 1, 1])
                    e_cod = ce1.text_input("Cod", value=item.codigo)
                    e_nom = ce2.text_input("Nombre", value=item.nombre)
                    e_cant = ce3.number_input("Cant", value=item.cantidad)
                    e_price = ce4.number_input("Precio", value=item.precio_unitario)
                    e_min = ce5.number_input("Min", value=item.min_stock)
                    
                    col_save, col_cancel = st.columns([1, 1])
                    if col_save.form_submit_button("💾 Guardar"):
                        updated = StockItem(
                            id=item.id,
                            codigo=e_cod,
                            nombre=e_nom,
                            categoria=item.categoria, 
                            cantidad=e_cant,
                            precio_unitario=e_price,
                            min_stock=e_min,
                            marca=item.marca # Preserve original marca
                        )
                        actualizar_producto(updated)
                        st.session_state.editing_product_id = None
                        st.rerun()
                    
                    if col_cancel.form_submit_button("❌ Cancelar"):
                        st.session_state.editing_product_id = None
                        st.rerun()
            st.divider()
        
        else:
            # --- VIEW MODE ROW ---
            # Define Status Color
            status_color = "🟢" if item.cantidad > item.min_stock else "🔴" if item.cantidad == 0 else "🟠"
            
            row = st.columns([0.5, 0.5, 2, 1, 1, 1])
            row[0].write(f"{item.id}")
            row[1].write(f"{item.codigo}")
            # Nombre + Category hint
            row[2].write(f"{item.nombre}") 
            
            # Stock with Indicator
            row[3].write(f"{status_color} {item.cantidad}")
            
            # Price
            row[4].write(f"${item.precio_unitario:,.0f}")
            
            # Actions
            actions_col = row[5]
            c_edit, c_del = actions_col.columns(2)
            
            # Edit Button
            if c_edit.button("✏️", key=f"btn_edit_{item.id}", help="Editar"):
                st.session_state.editing_product_id = item.id
                st.rerun()
                
            # Delete Button
            # Delete usually needs confirmation. 
            # Simple way: Click delete -> Sets a "Confirm state" for this ID?
            # Or use a popover if streamlit version supports it?
            # Assuming standard buttons for now.
            if c_del.button("🗑️", key=f"btn_del_{item.id}", help="Eliminar"):
                st.warning(f"¿Borrar {item.nombre}?")
                st.button("Sí, borrar", key=f"confirm_del_{item.id}", on_click=delete_handler, args=(item.id,))
                
    st.caption(f"Total de productos: {len(items)}")

def delete_handler(id):
    eliminar_producto(id)
    st.toast("Producto eliminado")

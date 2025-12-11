import streamlit as st
import pandas as pd
from typing import List
from src.services.cliente_service import leer_clientes, crear_cliente, actualizar_cliente, eliminar_cliente
from src.models import Cliente

from src.ui.state_manager import require_brand_selection

def render_clientes_page():
    # --- BRAND SELECTION BARRIER ---
    marca = require_brand_selection()
    if not marca:
        return

    st.title(f"👥 Gestión de Clientes ({marca})")

    # --- STATE MANAGEMENT ---
    if 'editing_client_id' not in st.session_state:
        st.session_state.editing_client_id = None
    if 'show_client_form' not in st.session_state:
        st.session_state.show_client_form = False

    # State for Inputs
    if 'new_cli_razon' not in st.session_state: st.session_state.new_cli_razon = ""
    if 'new_cli_cuit' not in st.session_state: st.session_state.new_cli_cuit = ""

    # --- CALLBACKS ---
    def submit_new_client():
        # Access bound variables from state
        new_razon = st.session_state.new_cli_razon
        new_cuit = st.session_state.new_cli_cuit
        
        if not new_razon:
            st.session_state.cli_msg = ("error", "Razón Social es obligatoria.")
            return

        try:
            cliente = Cliente(id=0, razon_social=new_razon, cuit_cuil=new_cuit, marca=marca)
            crear_cliente(cliente)
            st.session_state.cli_msg = ("success", f"Cliente creado en {marca}!")
            
            # Safe to clear/reset state here
            st.session_state.new_cli_razon = ""
            st.session_state.new_cli_cuit = ""
            st.session_state.show_client_form = False
        except Exception as e:
             st.session_state.cli_msg = ("error", f"Error: {e}")

    # --- 1. TOOLBAR ---
    col_tools, _ = st.columns([1, 4])
    if col_tools.button("➕ Nuevo Cliente", type="primary", use_container_width=True):
        st.session_state.show_client_form = not st.session_state.show_client_form

    # --- 2. CREATE FORM ---
    if 'cli_msg' in st.session_state:
        dtype, msg = st.session_state.pop('cli_msg')
        if dtype == 'error': st.error(msg)
        elif dtype == 'success': st.success(msg)

    if st.session_state.show_client_form:
        with st.container():
            st.markdown(f"### ✨ Alta de Cliente en {marca}")
            with st.form("create_client_form", clear_on_submit=False):
                c1, c2 = st.columns(2)
                # Use keys
                st.text_input("Razón Social", key="new_cli_razon")
                st.text_input("CUIT / CUIL (Opcional)", key="new_cli_cuit")
                
                st.form_submit_button("Guardar Cliente", on_click=submit_new_client)
            st.divider()

    # --- 3. LIST & ACTIONS ---
    try:
        clientes = leer_clientes(marca)
    except Exception as e:
        st.error(f"Error cargando clientes: {e}")
        clientes = []

    if not clientes:
        st.info(f"No hay clientes registrados en {marca}.")
        return

    # Header
    h_cols = st.columns([0.5, 3, 2, 1])
    h_cols[0].markdown("**ID**")
    h_cols[1].markdown("**Razón Social**")
    h_cols[2].markdown("**CUIT/CUIL**")
    h_cols[3].markdown("**Acciones**")
    st.divider()

    for cli in clientes:
        # EDIT MODE
        if st.session_state.editing_client_id == cli.id:
            with st.container():
                with st.form(f"edit_cli_{cli.id}"):
                    ce1, ce2 = st.columns(2)
                    e_razon = ce1.text_input("Razón Social", value=cli.razon_social)
                    e_cuit = ce2.text_input("CUIT/CUIL", value=cli.cuit_cuil if cli.cuit_cuil else "")
                    
                    col_save, col_cancel = st.columns([1, 1])
                    if col_save.form_submit_button("💾 Guardar"):
                        updated = Cliente(id=cli.id, razon_social=e_razon, cuit_cuil=e_cuit)
                        actualizar_cliente(updated)
                        st.session_state.editing_client_id = None
                        st.rerun()
                    
                    if col_cancel.form_submit_button("❌ Cancelar"):
                        st.session_state.editing_client_id = None
                        st.rerun()
            st.divider()
        else:
            # VIEW MODE
            row = st.columns([0.5, 3, 2, 1])
            row[0].write(f"{cli.id}")
            row[1].write(f"{cli.razon_social}")
            row[2].write(f"{cli.cuit_cuil if cli.cuit_cuil else '-'}")
            
            actions = row[3]
            ac1, ac2 = actions.columns(2)
            if ac1.button("✏️", key=f"edit_c_{cli.id}"):
                st.session_state.editing_client_id = cli.id
                st.rerun()
                
            if ac2.button("🗑️", key=f"del_c_{cli.id}"):
                st.warning(f"¿Borrar {cli.razon_social}?")
                st.button("Sí, borrar", key=f"conf_del_c_{cli.id}", on_click=delete_handler_c, args=(cli.id,))

def delete_handler_c(id):
    eliminar_cliente(id)
    st.toast("Cliente eliminado")

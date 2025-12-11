import streamlit as st

def require_brand_selection():
    """
    Renders the Brand Selection Buttons if no brand is selected in session_state.
    Returns the selected brand (str) if selected, or None if not.
    """
    if "marca_seleccionada" in st.session_state and st.session_state.marca_seleccionada:
        return st.session_state.marca_seleccionada

    st.markdown("## 👋 Bienvenido. Selecciona tu Marca de Trabajo:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Using a container to center or style if needed, 
        # but standard buttons expand well with use_container_width
        if st.button("VETA", type="primary", use_container_width=True):
            st.session_state.marca_seleccionada = "VETA"
            st.rerun()
            
    with col2:
        if st.button("VENETO", type="primary", use_container_width=True):
            st.session_state.marca_seleccionada = "VENETO"
            st.rerun()
            
    return None

def render_brand_reset_button_sidebar():
    """
    Renders a small button in the sidebar to reset the brand selection.
    """
    if "marca_seleccionada" in st.session_state and st.session_state.marca_seleccionada:
        st.sidebar.divider()
        st.sidebar.markdown(f"### Marca: {st.session_state.marca_seleccionada}")
        if st.sidebar.button("🔄 Cambiar de Marca", type="primary", use_container_width=True):
            st.session_state.marca_seleccionada = None
            st.rerun()

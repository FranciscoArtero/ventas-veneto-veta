import streamlit as st
import pandas as pd
from typing import List
from src.models import StockItem
from src.services.postgres_service import leer_stock, crear_producto, actualizar_producto, eliminar_producto

def get_stock_data():
    """Cache-helper o llamada directa para obtener datos."""
    try:
        data = leer_stock()
        return data
    except Exception as e:
        st.error(f"Error leyendo Stock de Google Sheets: {e}")
        return []

def render_stock_page():
    st.title("Gestión de Stock")
    
    # ---------------------------------------------------------
    # 1. READ & VISUALIZE
    # ---------------------------------------------------------
    st.subheader("Inventario Actual")

    # Boton de recarga manual
    if st.button("🔄 Recargar Datos"):
        st.cache_data.clear()
        st.rerun()

    items: List[StockItem] = get_stock_data()
    
    if not items:
        st.info("No hay ítems en el stock o no se pudo conectar.")
    else:
        # Preparamos DataFrame para visualización
        data_dicts = []
        for item in items:
            estado = "OK" if item.cantidad >= 5 else "BAJO STOCK"
            data_dicts.append({
                "ID": item.id,
                "Modelo": item.nombre,  # Asumimos que nombre es el modelo
                "Código": item.codigo,
                "Categoría": item.categoria,
                "Cantidad": item.cantidad,
                "Precio Unitario": item.precio_unitario,
                "ESTADO_CALC": estado # Para logica visual
            })
            
        df = pd.DataFrame(data_dicts)
        
        # Color styling
        def color_status(val):
            color = 'green' if val == 'OK' else 'red'
            return f'color: {color}; font-weight: bold'

        # Mostramos tabla con estilo (Pandas Styler no es full interactivo en streamlit para sort, 
        # pero st.dataframe sí. Para colorear celdas específicas en st.dataframe usamos column_config o style)
        # Vamos a usar st.dataframe con column styling simple si es posible, o style.applymap
        
        # Streamlit permite config de columnas. Para el color del texto de ESTADO, podemos usar pandas style.
        # Pero si queremos sorting interactivo completo, st.dataframe es mejor.
        
        # Estrategia: Añadir columna "Estado Visual" con emojis o texto
        df["ESTADO"] = df["ESTADO_CALC"] # Simple texto
        
        # Reordenar columnas visuales
        cols = ["ID", "Modelo", "Cantidad", "Precio Unitario", "ESTADO"]
        df_display = df[cols].copy()

        # Aplicamos estilo visual condicional usando pandas Styler
        styler = df_display.style.applymap(
            lambda x: "color: red; font-weight: bold" if x == "BAJO STOCK" else "color: green; font-weight: bold",
            subset=["ESTADO"]
        )
        
        st.dataframe(
            styler, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Precio Unitario": st.column_config.NumberColumn(format="$%.2f")
            }
        )

    st.divider()

    # ---------------------------------------------------------
    # 2. CREATE (Nuevo Producto)
    # ---------------------------------------------------------
    st.subheader("Agregar Nuevo Producto")
    with st.expander("📝 Formulario de Alta"):
        with st.form("new_product_form"):
            c1, c2 = st.columns(2)
            new_id = c1.number_input("ID (Único)", min_value=1, step=1)
            new_codigo = c2.text_input("Código SKU")
            new_nombre = st.text_input("Nombre / Modelo")
            new_categoria = st.text_input("Categoría")
            c3, c4 = st.columns(2)
            new_cantidad = c3.number_input("Cantidad Inicial", min_value=0, step=1)
            new_precio = c4.number_input("Precio Unitario", min_value=0.0, step=0.1)
            # Stock minimo default = 5
            
            submitted = st.form_submit_button("Guardar Producto")
            if submitted:
                # Validar ID unico (simple check local, idealmente en backend)
                existing_ids = [i.id for i in items]
                if new_id in existing_ids:
                    st.error(f"El ID {new_id} ya existe.")
                elif not new_nombre or not new_codigo:
                    st.error("Nombre y Código son obligatorios.")
                else:
                    new_item = StockItem(
                        id=new_id,
                        codigo=new_codigo,
                        nombre=new_nombre,
                        categoria=new_categoria,
                        cantidad=new_cantidad,
                        precio_unitario=new_precio,
                        min_stock=5
                    )
                    try:
                        crear_producto(new_item)
                        st.success("Producto creado exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando producto: {e}")

    # ---------------------------------------------------------
    # 3. UPDATE & DELETE (Gestión)
    # ---------------------------------------------------------
    st.subheader("Modificar / Eliminar Producto")
    
    if items:
        # Selector de producto para editar/eliminar
        # Creamos una lista de strings para el selectbox
        item_options = {f"{i.id} - {i.nombre}": i for i in items}
        selected_option = st.selectbox("Seleccionar Producto", options=list(item_options.keys()))
        
        if selected_option:
            selected_item: StockItem = item_options[selected_option]
            
            # Pestañas para acciones
            tab_edit, tab_delete = st.tabs(["Editar Stock/Precio", "Eliminar"])
            
            with tab_edit:
                st.write(f"Editando: **{selected_item.nombre}**")
                
                with st.form("edit_form"):
                    col_e1, col_e2 = st.columns(2)
                    edit_cantidad = col_e1.number_input(
                        "Nueva Cantidad", 
                        value=selected_item.cantidad, 
                        step=1
                    )
                    edit_precio = col_e2.number_input(
                        "Nuevo Precio", 
                        value=float(selected_item.precio_unitario), 
                        step=0.1
                    )
                    
                    if st.form_submit_button("Actualizar"):
                        # Rebuild full item because sqlite service expects full Object
                        # We use the selected_item as base
                        updated_item = StockItem(
                            id=selected_item.id,
                            codigo=selected_item.codigo,
                            nombre=selected_item.nombre,
                            categoria=selected_item.categoria,
                            cantidad=edit_cantidad,
                            precio_unitario=edit_precio,
                            min_stock=selected_item.min_stock
                        )
                        
                        try:
                            actualizar_producto(updated_item)
                            st.success("Producto actualizado correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error actualizando: {e}")

            with tab_delete:
                st.warning(f"¿Estás seguro que deseas eliminar el producto **{selected_item.nombre}** (ID: {selected_item.id})?")
                st.write("Esta acción no se puede deshacer.")
                if st.button("ELIMINAR DEFINITIVAMENTE", type="primary"):
                    try:
                        eliminar_producto(selected_item.id)
                        st.success(f"Producto {selected_item.id} eliminado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error eliminando: {e}")

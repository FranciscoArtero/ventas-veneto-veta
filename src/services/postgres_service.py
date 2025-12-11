"""
PostgreSQL Service Layer for Ventas Veta.

INSTRUCCIONES DE CONFIGURACIÓN (SUPABASE / POSTGRESQL):
-------------------------------------------------------
1.  **Crear Proyecto:** Crea una cuenta en Supabase (o tu proveedor preferido) y crea un nuevo proyecto.
2.  **Copiar Connection String:** Ve a los ajustes de la base de datos (Database Settings -> Connection Pooling o URI) y copia la URL de conexión.
    Debe verse como: `postgresql://postgres:[PASSWORD]@db.project.supabase.co:5432/postgres`
3.  **Configurar Secretos:**
    -   Opción A (Local/Streamlit Cloud): Crea un archivo `.streamlit/secrets.toml` en la raíz del proyecto y agrega:
        ```toml
        DB_URL_POSTGRES = "postgresql://postgres:[PASSWORD]@db.project.supabase.co:5432/postgres"
        ```
    -   Opción B (Variables de Entorno): Configura la variable de entorno `DB_URL_POSTGRES` con el mismo valor.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Optional
try:
    import streamlit as st
except ImportError:
    st = None

from ..models import StockItem, Venta, VentaItem

def get_connection():
    """Establishes a connection to the PostgreSQL database."""
    db_url = None
    
    # Priority 1: Streamlit Secrets
    if st is not None:
        try:
            # Check if secrets attribute exists (it might verify context)
            if hasattr(st, "secrets") and "DB_URL_POSTGRES" in st.secrets:
                db_url = st.secrets["DB_URL_POSTGRES"]
        except Exception:
            pass # Ignore if strict streamlit check fails

    # Priority 2: Environment Variable
    if not db_url:
        db_url = os.getenv("DB_URL_POSTGRES")

    if not db_url:
        # Fallback for dev/testing if needed, or raise error
        raise ValueError("DB_URL_POSTGRES is not set in secrets or environment.")

    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Initializes the database schema if it doesn't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Tabla STOCK
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                id SERIAL PRIMARY KEY,
                codigo TEXT,
                nombre TEXT NOT NULL,
                categoria TEXT,
                cantidad INTEGER DEFAULT 0,
                precio_unitario DECIMAL(10, 2) DEFAULT 0.0,
                min_stock INTEGER DEFAULT 5,
                marca TEXT NOT NULL DEFAULT 'VETA'
            )
        """)

        # Tabla VENTAS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id SERIAL PRIMARY KEY,
                fecha TEXT NOT NULL,
                cliente TEXT,
                total_bruto DECIMAL(10, 2) DEFAULT 0.0,
                descuento_porcentaje DECIMAL(5, 2) DEFAULT 0.0,
                total_neto DECIMAL(10, 2) DEFAULT 0.0,
                estado TEXT DEFAULT 'confirmada',
                estado_facturacion TEXT DEFAULT 'No Facturado',
                marca TEXT NOT NULL DEFAULT 'VETA',
                tipo_venta TEXT DEFAULT 'Venta Directa'
            )
        """)
        
        # Tabla VENTAS_ITEMS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_items (
                id SERIAL PRIMARY KEY,
                venta_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_unitario DECIMAL(10, 2) NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL,
                marca TEXT NOT NULL DEFAULT 'VETA',
                CONSTRAINT fk_venta FOREIGN KEY (venta_id) REFERENCES ventas (id),
                CONSTRAINT fk_producto FOREIGN KEY (producto_id) REFERENCES stock (id)
            )
        """)

        # Tabla CLIENTES
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                razon_social TEXT NOT NULL,
                cuit_cuil TEXT,
                fecha_creacion TEXT,
                marca TEXT NOT NULL DEFAULT 'VETA'
            )
        """)

        # Tabla CONCESIONARIOS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concesionarios (
                id SERIAL PRIMARY KEY,
                nombre_socio TEXT NOT NULL UNIQUE,
                cuit_cuil TEXT,
                contacto TEXT,
                marca TEXT NOT NULL
            )
        """)

        # Tabla CONCESION_STOCK
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concesion_stock (
                id SERIAL PRIMARY KEY,
                concesionario_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                marca TEXT NOT NULL,
                cantidad_disponible DECIMAL(10, 2) NOT NULL,
                fecha_salida TEXT,
                CONSTRAINT fk_concesionario FOREIGN KEY (concesionario_id) REFERENCES concesionarios (id)
            )
        """)
        
        conn.commit()
    except Exception as e:
        print(f"Error initializing DB: {e}")
        # Consider re-raising if critical
    finally:
        if 'conn' in locals(): conn.close()

# --- STOCK CRUD ---

def leer_stock(marca: Optional[str] = None) -> List[StockItem]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if marca:
            cursor.execute("SELECT * FROM stock WHERE marca = %s", (marca,))
        else:
            cursor.execute("SELECT * FROM stock")
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append(StockItem(
                id=row['id'],
                codigo=row['codigo'] if row['codigo'] else "",
                nombre=row['nombre'],
                categoria=row['categoria'] if row['categoria'] else "",
                cantidad=row['cantidad'],
                precio_unitario=float(row['precio_unitario']),
                min_stock=row['min_stock'],
                marca=row['marca']
            ))
        return items
    finally:
        conn.close()

def crear_producto(item: StockItem):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        code_val = item.codigo
        if code_val.isdigit():
             code_val = code_val.zfill(2)

        cursor.execute("""
            INSERT INTO stock (codigo, nombre, categoria, cantidad, precio_unitario, min_stock, marca)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (code_val, item.nombre, item.categoria, item.cantidad, item.precio_unitario, item.min_stock, item.marca))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def actualizar_producto(item: StockItem):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        code_val = item.codigo
        if code_val.isdigit():
             code_val = code_val.zfill(2)

        cursor.execute("""
            UPDATE stock 
            SET codigo = %s, nombre = %s, categoria = %s, cantidad = %s, precio_unitario = %s, min_stock = %s, marca = %s
            WHERE id = %s
        """, (code_val, item.nombre, item.categoria, item.cantidad, item.precio_unitario, item.min_stock, item.marca, item.id))
        
        if cursor.rowcount == 0:
            raise ValueError(f"Producto ID {item.id} no encontrado.")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def eliminar_producto(item_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM stock WHERE id = %s", (item_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"Producto ID {item_id} no encontrado.")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- SALES CRUD ---

def leer_ventas(marca: Optional[str] = None) -> List[Venta]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if marca:
            cursor.execute("SELECT * FROM ventas WHERE marca = %s ORDER BY id DESC", (marca,))
        else:
            cursor.execute("SELECT * FROM ventas ORDER BY id DESC")
        rows = cursor.fetchall()
        
        ventas = []
        for row in rows:
            try:
                # If using TEXT for date, parse it.
                fecha_obj = datetime.fromisoformat(row['fecha'])
            except ValueError:
                 fecha_obj = datetime.now()

            ventas.append(Venta(
                id=row['id'],
                fecha=fecha_obj,
                cliente=row['cliente'],
                total_bruto=float(row['total_bruto']),
                descuento_porcentaje=float(row['descuento_porcentaje']),
                total_neto=float(row['total_neto']),
                estado=row['estado'],
                estado_facturacion=row.get('estado_facturacion', "No Facturado"),
                marca=row['marca']
            ))
        return ventas
    finally:
        conn.close()

def leer_items_por_venta(venta_id: int) -> List[VentaItem]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM ventas_items WHERE venta_id = %s", (venta_id,))
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append(VentaItem(
                id=row['id'],
                venta_id=row['venta_id'],
                producto_id=row['producto_id'],
                cantidad=row['cantidad'],
                precio_unitario=float(row['precio_unitario']),
                subtotal=float(row['subtotal']),
                marca=row.get('marca', 'VETA')
            ))
        return items
    finally:
        conn.close()

def actualizar_estado_facturacion(venta_id: int, estado: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE ventas SET estado_facturacion = %s WHERE id = %s", (estado, venta_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def leer_ventas_items(marca: Optional[str] = None) -> List[VentaItem]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if marca:
            cursor.execute("SELECT * FROM ventas_items WHERE marca = %s", (marca,))
        else:
            cursor.execute("SELECT * FROM ventas_items")
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append(VentaItem(
                id=row['id'],
                venta_id=row['venta_id'],
                producto_id=row['producto_id'],
                cantidad=row['cantidad'],
                precio_unitario=float(row['precio_unitario']),
                subtotal=float(row['subtotal']),
                marca=row['marca']
            ))
        return items
    finally:
        conn.close()

def get_next_venta_id() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Note: SERIAL in postgres creates gaps, so this logic is just an estimation for UI.
        # Real IDs are assigned on INSERT.
        cursor.execute("SELECT MAX(id) FROM ventas")
        row = cursor.fetchone()
        val = row['max'] if row and row['max'] else 0
        return val + 1
    finally:
        conn.close()

def get_next_venta_item_id() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(id) FROM ventas_items")
        row = cursor.fetchone()
        val = row['max'] if row and row['max'] else 0
        return val + 1
    finally:
        conn.close()

def registrar_venta(venta: Venta, items: List[VentaItem]):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Validation & Stock Update
        for item in items:
            cursor.execute("SELECT cantidad, nombre FROM stock WHERE id = %s", (item.producto_id,))
            res = cursor.fetchone()
            if not res:
                raise ValueError(f"Producto ID {item.producto_id} no existe.")
            
            stock_actual, nombre_prod = res['cantidad'], res['nombre']
            
            if stock_actual < item.cantidad:
                raise ValueError(f"Stock insuficiente para {nombre_prod}. Hay {stock_actual}, pides {item.cantidad}.")
            
            # Update
            new_stock = stock_actual - item.cantidad
            cursor.execute("UPDATE stock SET cantidad = %s WHERE id = %s", (new_stock, item.producto_id))

        # 2. Insert Header with RETURNING id
        cursor.execute("""
            INSERT INTO ventas (fecha, cliente, total_bruto, descuento_porcentaje, total_neto, estado, estado_facturacion, marca, tipo_venta)
            VALUES (%s, %s, %s, %s, %s, %s, 'No Facturado', %s, %s)
            RETURNING id
        """, (venta.fecha.isoformat(), venta.cliente, venta.total_bruto, venta.descuento_porcentaje, venta.total_neto, venta.estado, venta.marca, venta.tipo_venta))
        
        venta_inserted_id = cursor.fetchone()['id']
        
        # 3. Insert Items
        for item in items:
             cursor.execute("""
                INSERT INTO ventas_items (venta_id, producto_id, cantidad, precio_unitario, subtotal, marca)
                VALUES (%s, %s, %s, %s, %s, %s)
             """, (venta_inserted_id, item.producto_id, item.cantidad, item.precio_unitario, item.subtotal, venta.marca))
        
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def actualizar_venta_totales(venta_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Sum subtotals
        cursor.execute("SELECT SUM(subtotal) FROM ventas_items WHERE venta_id = %s", (venta_id,))
        res = cursor.fetchone()
        # In Postgres SUM can return Decimal
        new_bruto = float(res['sum']) if res and res['sum'] is not None else 0.0
        
        # Get discount
        cursor.execute("SELECT descuento_porcentaje FROM ventas WHERE id = %s", (venta_id,))
        disc = float(cursor.fetchone()['descuento_porcentaje'])
        
        new_neto = new_bruto * (1 - disc/100)
        
        cursor.execute("UPDATE ventas SET total_bruto = %s, total_neto = %s WHERE id = %s", (new_bruto, new_neto, venta_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def eliminar_venta(venta_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get Sale Info
        cursor.execute("SELECT * FROM ventas WHERE id = %s", (venta_id,))
        venta = cursor.fetchone()
        if not venta:
            raise ValueError("Venta no encontrada")
            
        # Get Items
        cursor.execute("SELECT * FROM ventas_items WHERE venta_id = %s", (venta_id,))
        items = cursor.fetchall()
        
        tipo = venta['tipo_venta']
        cliente = venta['cliente']
        
        # RESTORE STOCK
        for item in items:
            prod_id = item['producto_id']
            qty = item['cantidad']
            
            if tipo == 'Venta Concesión':
                name_clean = cliente.replace(" (Concesión)", "").strip()
                cursor.execute("SELECT id FROM concesionarios WHERE nombre_socio = %s", (name_clean,))
                conc_row = cursor.fetchone()
                if conc_row:
                    conc_id = conc_row['id']
                    # Restore to Concession Stock
                    cursor.execute("SELECT id, cantidad_disponible FROM concesion_stock WHERE concesionario_id = %s AND producto_id = %s", (conc_id, prod_id))
                    cs_row = cursor.fetchone()
                    if cs_row:
                        new_q = float(cs_row['cantidad_disponible']) + qty
                        cursor.execute("UPDATE concesion_stock SET cantidad_disponible = %s WHERE id = %s", (new_q, cs_row['id']))
            else:
                # Venta Directa -> Restore to Main Stock
                cursor.execute("SELECT cantidad FROM stock WHERE id = %s", (prod_id,))
                stk_row = cursor.fetchone()
                if stk_row:
                    new_q = stk_row['cantidad'] + qty
                    cursor.execute("UPDATE stock SET cantidad = %s WHERE id = %s", (new_q, prod_id))

        # Delete Record
        cursor.execute("DELETE FROM ventas_items WHERE venta_id = %s", (venta_id,))
        cursor.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def actualizar_cantidad_item_venta(venta_id: int, item_id: int, new_qty: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get Item Info
        cursor.execute("SELECT * FROM ventas_items WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        if not item: raise ValueError("Item no encontrado")
        
        old_qty = item['cantidad']
        prod_id = item['producto_id']
        delta = new_qty - old_qty
        
        if delta == 0: return

        # Get Sale Info
        cursor.execute("SELECT * FROM ventas WHERE id = %s", (venta_id,))
        venta = cursor.fetchone()
        tipo = venta['tipo_venta']
        
        # STOCK CHECK & UPDATE
        if tipo == 'Venta Concesión':
            cliente = venta['cliente']
            name_clean = cliente.replace(" (Concesión)", "").strip()
            cursor.execute("SELECT id FROM concesionarios WHERE nombre_socio = %s", (name_clean,))
            conc_row = cursor.fetchone()
            if not conc_row: raise ValueError(f"Concesionario {name_clean} no encontrado")
            conc_id = conc_row['id']
            
            cursor.execute("SELECT id, cantidad_disponible FROM concesion_stock WHERE concesionario_id = %s AND producto_id = %s", (conc_id, prod_id))
            cs_row = cursor.fetchone()
            if not cs_row: raise ValueError("Stock de concesión no encontrado")
            
            current_disp = float(cs_row['cantidad_disponible'])
            if delta > 0 and current_disp < delta:
                 raise ValueError(f"Stock insuficiente en concesión. Disp: {current_disp}")
            
            # Update Stock
            new_stock = current_disp - delta
            cursor.execute("UPDATE concesion_stock SET cantidad_disponible = %s WHERE id = %s", (new_stock, cs_row['id']))
            
        else:
            # Main Stock
            cursor.execute("SELECT cantidad FROM stock WHERE id = %s", (prod_id,))
            stk_row = cursor.fetchone()
            if not stk_row: raise ValueError("Producto no encontrado")
            
            current_disp = stk_row['cantidad']
            if delta > 0 and current_disp < delta:
                raise ValueError(f"Stock insuficiente. Disp: {current_disp}")
                
            new_stock = current_disp - delta
            cursor.execute("UPDATE stock SET cantidad = %s WHERE id = %s", (new_stock, prod_id))
            
        # UPDATE ITEM
        # Recalculate Subtotal
        new_subtotal = float(item['precio_unitario']) * new_qty
        cursor.execute("UPDATE ventas_items SET cantidad = %s, subtotal = %s WHERE id = %s", (new_qty, new_subtotal, item_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    actualizar_venta_totales(venta_id)

def actualizar_descuento_venta(venta_id: int, new_discount: float):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE ventas SET descuento_porcentaje = %s WHERE id = %s", (new_discount, venta_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    actualizar_venta_totales(venta_id)

from datetime import datetime
from typing import List, Dict, Optional
from src.services.postgres_service import get_connection
from ..models import Concesionario, Venta, VentaItem

# Wholesale Discount Rate (30% off)
WHOLESALE_DISCOUNT = 0.30

def get_concesionarios(marca: str) -> List[Concesionario]:
    """Obtiene todos los concesionarios de una marca."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM concesionarios WHERE marca = %s", (marca,))
    rows = cursor.fetchall()
    conn.close()
    return [Concesionario(**dict(row)) for row in rows]

def crear_concesionario(nombre: str, cuit: str, contacto: str, marca: str):
    """Crea un nuevo socio/concesionario."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO concesionarios (nombre_socio, cuit_cuil, contacto, marca) VALUES (%s, %s, %s, %s)", 
                       (nombre, cuit, contacto, marca))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def actualizar_concesionario(id: int, nombre: str, cuit: str, contacto: str):
    """Actualiza datos de un concesionario."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE concesionarios 
            SET nombre_socio = %s, cuit_cuil = %s, contacto = %s
            WHERE id = %s
        ''', (nombre, cuit, contacto, id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def eliminar_concesionario(id: int):
    """Elimina un concesionario si no tiene stock asignado."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT count(*) FROM concesion_stock WHERE concesionario_id = %s AND cantidad_disponible > 0", (id,))
        # Postgres returns count in 'count' column usually, or distinct row
        row = cursor.fetchone()
        count_val = row['count'] if row and 'count' in row else list(row.values())[0]

        if count_val > 0:
            raise ValueError("No se puede eliminar socio con stock en consignación activo.")
            
        cursor.execute("DELETE FROM concesionarios WHERE id = %s", (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def registrar_salida_concesion(concesionario_id: int, marca: str, items: List[Dict]):
    """
    Mueve stock del Depósito Principal al Stock del Concesionario.
    
    Args:
        concesionario_id (int): ID del socio.
        marca (str): Marca de la operación.
        items (List[Dict]): Lista de dicts {'producto_id': int, 'cantidad': int}.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        for item in items:
            prod_id = item['producto_id']
            qty = item['cantidad']
            
            # 1. Check Main Stock
            cursor.execute("SELECT cantidad, nombre FROM stock WHERE id = %s", (prod_id,))
            res = cursor.fetchone()
            if not res:
                raise ValueError(f"Producto ID {prod_id} no encontrado.")
            
            stock_actual, nombre_prod = res['cantidad'], res['nombre']
            if stock_actual < qty:
                raise ValueError(f"Stock insuficiente en Depósito para {nombre_prod}. Hay {stock_actual}, se piden {qty}.")
            
            # 2. Update Main Stock (Subtract)
            new_main_stock = stock_actual - qty
            cursor.execute("UPDATE stock SET cantidad = %s WHERE id = %s", (new_main_stock, prod_id))
            
            # 3. Update Concesion Stock (Add)
            cursor.execute('''
                SELECT id, cantidad_disponible FROM concesion_stock 
                WHERE concesionario_id = %s AND producto_id = %s
            ''', (concesionario_id, prod_id))
            row_conc = cursor.fetchone()
            
            if row_conc:
                # Update existing
                current_conc_qty = float(row_conc['cantidad_disponible'])
                new_conc_qty = current_conc_qty + qty
                cursor.execute("UPDATE concesion_stock SET cantidad_disponible = %s, fecha_salida = %s WHERE id = %s", 
                               (new_conc_qty, datetime.now().isoformat(), row_conc['id']))
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO concesion_stock (concesionario_id, producto_id, marca, cantidad_disponible, fecha_salida)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (concesionario_id, prod_id, marca, qty, datetime.now().isoformat()))
        
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def confirmar_venta_concesion(concesionario_id: int, marca: str, items_vendidos: List[Dict]):
    """
    Registra una venta desde el stock del Concesionario.
    
    Args:
        items_vendidos: Lista de dicts {'producto_id': int, 'cantidad': int}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        total_bruto = 0.0
        total_neto = 0.0
        venta_items_data = []

        # Get Dealer Name for Record
        cursor.execute("SELECT nombre_socio FROM concesionarios WHERE id = %s", (concesionario_id,))
        dealer_row = cursor.fetchone()
        dealer_name = dealer_row['nombre_socio'] if dealer_row else f"Concesionario {concesionario_id}"

        # 1. Validate & Calc Loop
        for item in items_vendidos:
            prod_id = item['producto_id']
            qty = item['cantidad']
            
            # Check Concesion Stock
            cursor.execute('''
                SELECT cantidad_disponible FROM concesion_stock 
                WHERE concesionario_id = %s AND producto_id = %s
            ''', (concesionario_id, prod_id))
            row_conc = cursor.fetchone()
            
            available = float(row_conc['cantidad_disponible']) if row_conc else 0
            if available < qty:
                raise ValueError(f"Stock insuficiente en Concesionario para Producto {prod_id}. Hay {available}.")
                
            # Get Price from Main Stock (List Price)
            cursor.execute("SELECT precio_unitario, nombre FROM stock WHERE id = %s", (prod_id,))
            prod_row = cursor.fetchone()
            list_price = float(prod_row['precio_unitario'])
            
            # Apply Wholesale Logic
            wholesale_price = list_price * (1 - WHOLESALE_DISCOUNT)
            item_subtotal = wholesale_price * qty
            
            total_bruto += (list_price * qty) 
            total_neto += item_subtotal

            venta_items_data.append({
                'producto_id': prod_id,
                'cantidad': qty,
                'precio_unitario': wholesale_price,
                'subtotal': item_subtotal
            })

            # 2. Update Concesion Stock (Subtract)
            new_conc_qty = available - qty
            cursor.execute("UPDATE concesion_stock SET cantidad_disponible = %s WHERE concesionario_id = %s AND producto_id = %s", 
                           (new_conc_qty, concesionario_id, prod_id))

        # 3. Create Sale Record with RETURNING id
        cursor.execute('''
            INSERT INTO ventas (fecha, cliente, total_bruto, descuento_porcentaje, total_neto, estado, estado_facturacion, marca, tipo_venta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (datetime.now().isoformat(), f"{dealer_name} (Concesión)", total_bruto, 30.0, total_neto, 'confirmada', 'No Facturado', marca, 'Venta Concesión'))
        
        venta_id = cursor.fetchone()['id']
        
        # 4. Insert Sale Items
        for v_item in venta_items_data:
            cursor.execute('''
                INSERT INTO ventas_items (venta_id, producto_id, cantidad, precio_unitario, subtotal, marca)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (venta_id, v_item['producto_id'], v_item['cantidad'], v_item['precio_unitario'], v_item['subtotal'], marca))
            
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def leer_stock_concesion(concesionario_id: int):
    """Devuelve el stock disponible para un concesionario específico."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT cs.*, s.nombre as producto_nombre, s.codigo as producto_codigo
        FROM concesion_stock cs
        JOIN stock s ON cs.producto_id = s.id
        WHERE cs.concesionario_id = %s AND cs.cantidad_disponible > 0
    ''', (concesionario_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def devolver_stock_concesion(concesionario_id: int, producto_id: int, cantidad: float):
    """
    Devuelve stock del Concesionario al Depósito Principal.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Check Concesion Stock
        cursor.execute('''
            SELECT id, cantidad_disponible FROM concesion_stock 
            WHERE concesionario_id = %s AND producto_id = %s
        ''', (concesionario_id, producto_id))
        row_conc = cursor.fetchone()
        
        if not row_conc:
            raise ValueError("No se encontró registro de stock en concesión.")
            
        current_conc = float(row_conc['cantidad_disponible'])
        if current_conc < cantidad:
            raise ValueError(f"No se puede devolver {cantidad}. Solo hay {current_conc} en consignación.")
            
        # 2. Update Concesion Stock (Decrease)
        new_conc = current_conc - cantidad
        cursor.execute("UPDATE concesion_stock SET cantidad_disponible = %s WHERE id = %s", (new_conc, row_conc['id']))
        
        # 3. Update Main Stock (Increase)
        cursor.execute("SELECT cantidad FROM stock WHERE id = %s", (producto_id,))
        row_main = cursor.fetchone()
        if row_main:
            new_main = row_main['cantidad'] + cantidad
            cursor.execute("UPDATE stock SET cantidad = %s WHERE id = %s", (new_main, producto_id))
        else:
             raise ValueError("Producto original no encontrado en depósito principal.")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def devolver_stock_concesion_masivo(concesionario_id: int, items: List[Dict]):
    """
    Devolución masiva de ítems de concesión a stock principal.
    items: [{'producto_id': int, 'cantidad': float}]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for item in items:
            prod_id = item['producto_id']
            qty = item['cantidad']
            
            # 1. Check Concesion Stock
            cursor.execute('''
                SELECT id, cantidad_disponible FROM concesion_stock 
                WHERE concesionario_id = %s AND producto_id = %s
            ''', (concesionario_id, prod_id))
            row_conc = cursor.fetchone()
            
            if not row_conc:
                raise ValueError(f"Producto {prod_id}: No se encontró registro en concesión.")
                
            current_conc = float(row_conc['cantidad_disponible'])
            if current_conc < qty:
                raise ValueError(f"Producto {prod_id}: No se puede devolver {qty}. Solo hay {current_conc}.")
                
            # 2. Update Concesion Stock (Decrease)
            new_conc = current_conc - qty
            cursor.execute("UPDATE concesion_stock SET cantidad_disponible = %s WHERE id = %s", (new_conc, row_conc['id']))
            
            # 3. Update Main Stock (Increase)
            cursor.execute("SELECT cantidad FROM stock WHERE id = %s", (prod_id,))
            row_main = cursor.fetchone()
            if row_main:
                new_main = row_main['cantidad'] + qty
                cursor.execute("UPDATE stock SET cantidad = %s WHERE id = %s", (new_main, prod_id))
            else:
                 raise ValueError(f"Producto {prod_id} no encontrado en depósito principal.")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

import psycopg2
from datetime import datetime
from typing import List, Optional
from src.models import Cliente
from src.services.postgres_service import get_connection

def leer_clientes(marca: Optional[str] = None) -> List[Cliente]:
    """Lee clientes. Si marca es None, lee todos. Ordenados por razón social."""
    conn = get_connection()
    cursor = conn.cursor()
    if marca:
        cursor.execute("SELECT * FROM clientes WHERE marca = %s ORDER BY razon_social ASC", (marca,))
    else:
        cursor.execute("SELECT * FROM clientes ORDER BY razon_social ASC") # All brands
    rows = cursor.fetchall()
    conn.close()
    
    clientes = []
    for row in rows:
        fecha = None
        if row['fecha_creacion']:
            try:
                fecha = datetime.fromisoformat(row['fecha_creacion'])
            except:
                pass
                
        clientes.append(Cliente(
            id=row['id'],
            razon_social=row['razon_social'],
            cuit_cuil=row['cuit_cuil'],
            fecha_creacion=fecha,
            marca=row['marca']
        ))
    return clientes

def crear_cliente(cliente: Cliente):
    """Crea un nuevo cliente."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        current_time = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO clientes (razon_social, cuit_cuil, fecha_creacion, marca)
            VALUES (%s, %s, %s, %s)
        ''', (cliente.razon_social, cliente.cuit_cuil, current_time, cliente.marca))
        conn.commit()
    except psycopg2.IntegrityError:
        raise ValueError(f"El cliente '{cliente.razon_social}' ya existe.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def actualizar_cliente(cliente: Cliente):
    """Actualiza un cliente existente."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE clientes 
            SET razon_social = %s, cuit_cuil = %s
            WHERE id = %s
        ''', (cliente.razon_social, cliente.cuit_cuil, cliente.id))
        
        if cursor.rowcount == 0:
            raise ValueError(f"Cliente ID {cliente.id} no encontrado.")
            
        conn.commit()
    except psycopg2.IntegrityError:
        raise ValueError(f"Ya existe otro cliente con el nombre '{cliente.razon_social}'.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def eliminar_cliente(cliente_id: int):
    """Elimina un cliente por ID."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"Cliente ID {cliente_id} no encontrado.")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

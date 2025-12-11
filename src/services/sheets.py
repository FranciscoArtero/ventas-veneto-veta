import gspread
from typing import List, Optional
import os
from datetime import datetime
from ..models import StockItem, Venta, VentaItem
from ..config import SHEET_STOCK, SHEET_VENTAS, SHEET_VENTAS_ITEMS

def get_client():
    """Autentica y retorna cliente de gspread usando credentials.json o st.secrets."""
    credentials_path = "credentials.json"
    
    # 1. Try local file
    if os.path.exists(credentials_path):
        try:
            return gspread.service_account(filename=credentials_path)
        except Exception as e:
            print(f"Error con credentials.json: {e}")

    # 2. Try Streamlit Secrets (for Cloud Deployment)
    # We import streamlit here inside the function to avoid strict dependency if used elsewhere
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            # Create a dict from secrets and use it
            # gspread expects a dict or filename
            creds_dict = dict(st.secrets["gcp_service_account"])
            return gspread.service_account_from_dict(creds_dict)
    except ImportError:
        pass # Streamlit not installed or not in use
    except Exception as e:
        print(f"Error leyendo st.secrets: {e}")

    raise ValueError("No se encontraron credenciales válidas (credentials.json o st.secrets).")


def _ensure_sheet_exists(spreadsheet, sheet_name):
    """Creates the sheet if it doesn't exist, with default headers."""
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        # Define headers for known sheets
        headers = {
            SHEET_STOCK: ['id', 'codigo', 'nombre', 'categoria', 'cantidad', 'precio_unitario', 'min_stock'],
            SHEET_VENTAS: ['id', 'fecha', 'cliente', 'total_bruto', 'descuento_porcentaje', 'total_neto', 'estado'],
            SHEET_VENTAS_ITEMS: ['id', 'venta_id', 'producto_id', 'cantidad', 'precio_unitario', 'subtotal']
        }
        
        if sheet_name in headers:
            print(f"Creando hoja faltante: {sheet_name}")
            ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
            ws.append_row(headers[sheet_name])
            return ws
        else:
            raise ValueError(f"Hoja desconocida '{sheet_name}' y no se puede auto-crear.")

def _get_worksheet(sheet_name=SHEET_STOCK, spreadsheet_name="VENTAS VETA", spreadsheet_id=None):
    """Helper to get a worksheet. Uses ID if provided, else Name. Auto-creates if missing."""
    gc = get_client()
    try:
        if spreadsheet_id:
            sh = gc.open_by_key(spreadsheet_id)
        else:
            sh = gc.open(spreadsheet_name)
            
        return _ensure_sheet_exists(sh, sheet_name)
    except Exception as e:
        print(f"Error accediendo a hoja {sheet_name}: {e}")
        raise e

def _get_next_id(sheet_name: str, spreadsheet_id: str = None) -> int:
    """Calcula el siguiente ID basado en la columna 'id' (columna 1)."""
    try:
        ws = _get_worksheet(sheet_name, spreadsheet_id=spreadsheet_id)
        # Assuming ID is always in column 1
        col_values = ws.col_values(1)
        if len(col_values) <= 1: # Only header
            return 1
        
        # Filter non-numeric headers if any, convert to int
        ids = []
        for v in col_values[1:]:
            if str(v).isdigit():
                ids.append(int(v))
        
        return max(ids) + 1 if ids else 1
    except Exception as e:
        # Fallback if sheet is empty or error
        return 1

def leer_stock(sheet_name: str = SHEET_STOCK, spreadsheet_id: str = None) -> List[StockItem]:
    """
    Lee el stock desde la hoja especificada y retorna una lista de StockItem.
    """
    try:
        worksheet = _get_worksheet(sheet_name, spreadsheet_id=spreadsheet_id)
        records = worksheet.get_all_records()
        
        items = []
        for record in records:
            # Normalize keys to remove potential leading/trailing whitespace from Sheet headers
            clean_record = {k.strip(): v for k, v in record.items()}
            
            # Ensure proper type conversion
            item = StockItem(
                id=int(clean_record.get('id', 0)),
                codigo=str(clean_record.get('codigo', '')),
                nombre=str(clean_record.get('nombre', '')),
                categoria=str(clean_record.get('categoria', '')),
                cantidad=int(clean_record.get('cantidad', 0)),
                precio_unitario=float(clean_record.get('precio_unitario', 0.0)),
                min_stock=int(clean_record.get('min_stock', 5))
            )
            items.append(item)
            
        return items
    except Exception as e:
        print(f"Error leyendo stock: {e}")
        raise e

def leer_ventas(sheet_name: str = SHEET_VENTAS, spreadsheet_id: str = None) -> List[Venta]:
    """Lee el historial de ventas."""
    try:
        worksheet = _get_worksheet(sheet_name, spreadsheet_id=spreadsheet_id)
        records = worksheet.get_all_records()
        ventas = []
        for record in records:
            clean_record = {k.strip(): v for k, v in record.items()}
            # Handle date parsing safely
            fecha_val = clean_record.get('fecha')
            if isinstance(fecha_val, str):
                try:
                    fecha_obj = datetime.strptime(fecha_val, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    fecha_obj = datetime.now() # Fallback
            else:
                fecha_obj = fecha_val

            v = Venta(
                id=int(clean_record.get('id', 0)),
                fecha=fecha_obj,
                cliente=str(clean_record.get('cliente', '')),
                total_bruto=float(clean_record.get('total_bruto', 0.0)),
                descuento_porcentaje=float(clean_record.get('descuento_porcentaje', 0.0)),
                total_neto=float(clean_record.get('total_neto', 0.0)),
                estado=str(clean_record.get('estado', 'confirmada'))
            )
            ventas.append(v)
        return ventas
    except Exception as e:
        print(f"Error leyendo ventas: {e}")
        return []

def leer_ventas_items(sheet_name: str = SHEET_VENTAS_ITEMS, spreadsheet_id: str = None) -> List[VentaItem]:
    """Lee los items vendidos."""
    try:
        worksheet = _get_worksheet(sheet_name, spreadsheet_id=spreadsheet_id)
        records = worksheet.get_all_records()
        items = []
        for record in records:
            clean_record = {k.strip(): v for k, v in record.items()}
            i = VentaItem(
                id=int(clean_record.get('id', 0)),
                venta_id=int(clean_record.get('venta_id', 0)),
                producto_id=int(clean_record.get('producto_id', 0)),
                cantidad=int(clean_record.get('cantidad', 0)),
                precio_unitario=float(clean_record.get('precio_unitario', 0.0)),
                subtotal=float(clean_record.get('subtotal', 0.0))
            )
            items.append(i)
        return items
    except Exception as e:
        print(f"Error leyendo ventas items: {e}")
        return []

def crear_producto(item: StockItem, sheet_name: str = SHEET_STOCK, spreadsheet_id: str = None):
    """Agrega un nuevo producto al final de la hoja."""
    try:
        worksheet = _get_worksheet(sheet_name, spreadsheet_id=spreadsheet_id)
        
        # Helper to preserve leading zeros in codes logic: prepend ' if needed
        # Helper to preserve leading zeros in codes logic: prepend ' if needed
        code_val = item.codigo
        if code_val.isdigit():
             code_val = code_val.zfill(2)
             if code_val.startswith('0'):
                  code_val = f"'{code_val}"
                
        # Append row. Order must match columns: id, codigo, nombre, categoria, cantidad, precio_unitario, min_stock
        row = [item.id, code_val, item.nombre, item.categoria, item.cantidad, item.precio_unitario, item.min_stock]
        worksheet.append_row(row)
    except Exception as e:
        print(f"Error creando producto: {e}")
        raise e

def actualizar_producto(item: StockItem, sheet_name: str = SHEET_STOCK, spreadsheet_id: str = None):
    """Actualiza un producto existente buscando por ID."""
    try:
        worksheet = _get_worksheet(sheet_name, spreadsheet_id=spreadsheet_id)
        cell = worksheet.find(str(item.id), in_column=1) # Find cell with the ID ONLY in Col 1
        if cell:
            row_num = cell.row
            
            # Helper to preserve leading zeros in codes logic: prepend ' if needed
            code_val = item.codigo
            if code_val.isdigit():
                 code_val = code_val.zfill(2)
                 if code_val.startswith('0'):
                      code_val = f"'{code_val}"

            # Updating individually to be safe, assuming columns generic.
            # 1:id, 2:codigo, 3:nombre, 4:categoria, 5:cantidad, 6:precio, 7:min_stock
            worksheet.update_cell(row_num, 2, code_val)
            worksheet.update_cell(row_num, 3, item.nombre)
            worksheet.update_cell(row_num, 4, item.categoria)
            worksheet.update_cell(row_num, 5, item.cantidad)
            worksheet.update_cell(row_num, 6, item.precio_unitario)
            worksheet.update_cell(row_num, 7, item.min_stock)
        else:
            raise ValueError(f"Producto con ID {item.id} no encontrado.")
            
    except Exception as e:
        print(f"Error actualizando producto: {e}")
        raise e

def eliminar_producto(item_id: int, sheet_name: str = SHEET_STOCK, spreadsheet_id: str = None):
    """Elimina fisica un producto buscando por ID."""
    try:
        worksheet = _get_worksheet(sheet_name, spreadsheet_id=spreadsheet_id)
        cell = worksheet.find(str(item_id), in_column=1)
        if cell:
            worksheet.delete_rows(cell.row)
        else:
             raise ValueError(f"Producto con ID {item_id} no encontrado.")
    except Exception as e:
        print(f"Error eliminando producto: {e}")
        raise e

def registrar_venta(venta: Venta, items: List[VentaItem], spreadsheet_id: str = None):
    """
    Registra una venta completa:
    1. Descuenta stock.
    2. Guarda cabecera de venta.
    3. Guarda items de venta.
    """
    try:
        # 1. Update Stock
        # We fetch current stock again to ensure validity
        current_stock = leer_stock(SHEET_STOCK, spreadsheet_id)
        stock_map = {item.id: item for item in current_stock}
        
        # Client for batch updates if possible, but stepping one by one for simplicity and safety
        ws_stock = _get_worksheet(SHEET_STOCK, spreadsheet_id=spreadsheet_id)
        
        for v_item in items:
            s_item = stock_map.get(v_item.producto_id)
            if not s_item:
                raise ValueError(f"Producto ID {v_item.producto_id} no encontrado en stock.")
            
            if s_item.cantidad < v_item.cantidad:
                raise ValueError(f"Stock insuficiente para {s_item.nombre}. Stock: {s_item.cantidad}, Solicitado: {v_item.cantidad}")
            
            # Decrement local object
            s_item.cantidad -= v_item.cantidad
            # Update Remote
            actualizar_producto(s_item, SHEET_STOCK, spreadsheet_id)

        # 2. Save Venta Header
        ws_ventas = _get_worksheet(SHEET_VENTAS, spreadsheet_id=spreadsheet_id)
        venta_row = [
            venta.id,
            venta.fecha.strftime("%Y-%m-%d %H:%M:%S"),
            venta.cliente,
            venta.total_bruto,
            venta.descuento_porcentaje,
            venta.total_neto,
            venta.estado
        ]
        ws_ventas.append_row(venta_row)
        
        # 3. Save Venta Items
        ws_items = _get_worksheet(SHEET_VENTAS_ITEMS, spreadsheet_id=spreadsheet_id)
        items_rows = []
        for i in items:
            items_rows.append([
                i.id,
                i.venta_id,
                i.producto_id,
                i.cantidad,
                i.precio_unitario,
                i.subtotal
            ])
        ws_items.append_rows(items_rows)
        
        return True

    except Exception as e:
        print(f"Error registrando venta: {e}")
        raise e

def get_next_venta_id(spreadsheet_id: str = None) -> int:
    return _get_next_id(SHEET_VENTAS, spreadsheet_id) 

def get_next_venta_item_id(spreadsheet_id: str = None) -> int:
    return _get_next_id(SHEET_VENTAS_ITEMS, spreadsheet_id)

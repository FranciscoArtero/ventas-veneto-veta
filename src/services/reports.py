import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ..models import StockItem, Venta, VentaItem
from ..config import TIMEZONE

def get_kpis(stock: List[StockItem], ventas: List[Venta], reference_date: datetime = None) -> Dict[str, Any]:
    """
    Calcula KPIs principales:
    - MTD (Month to Date) Venta Neta: Ventas del mes/año de reference_date
    - YTD (Year to Date) Venta Neta: Ventas del año de reference_date
    - Transacciones Totales: (filtered by main logic, usually MTD in this context?)
      User asked for "Total de Transacciones" generally.
      If filtering by month, usually we want "Transactions in this month".
      Let's assume the 'ventas' passed here is the FULL history to allow YTD calc.
      So we return transactions for the MONTH.
    - Stock Crítico (items < min_stock)
    """
    if reference_date is None:
        reference_date = datetime.now()

    current_month = reference_date.month
    current_year = reference_date.year

    if not ventas:
        return {
            "mtd_neto": 0.0,
            "ytd_neto": 0.0,
            "total_transacciones": 0,
            "stock_critico": sum(1 for i in stock if i.cantidad <= i.min_stock)
        }

    df_ventas = pd.DataFrame([v.dict() for v in ventas])
    # Fix: Force UTC then convert to local
    df_ventas['fecha'] = pd.to_datetime(df_ventas['fecha'], utc=True).dt.tz_convert(TIMEZONE)

    # Filter MTD (Selected Month)
    mask_mtd = (df_ventas['fecha'].dt.month == current_month) & (df_ventas['fecha'].dt.year == current_year)
    mtd_neto = df_ventas.loc[mask_mtd, 'total_neto'].sum()
    mtd_transactions = df_ventas.loc[mask_mtd].shape[0]

    # Filter YTD (Selected Year)
    mask_ytd = (df_ventas['fecha'].dt.year == current_year)
    ytd_neto = df_ventas.loc[mask_ytd, 'total_neto'].sum()

    # Stock Critical
    stock_critico = sum(1 for i in stock if i.cantidad <= i.min_stock)

    return {
        "mtd_neto": mtd_neto,
        "ytd_neto": ytd_neto,
        "total_transacciones": mtd_transactions,
        "stock_critico": stock_critico
    }
def get_top_products(items: List[VentaItem], stock: List[StockItem], top_n=5) -> pd.DataFrame:
    """
    Top N productos más vendidos (unidades).
    Cruza con Stock para obtener nombres.
    """
    if not items:
        return pd.DataFrame()

    df_items = pd.DataFrame([i.dict() for i in items])
    
    # Aggregation
    top_sold = df_items.groupby('producto_id')['cantidad'].sum().reset_index()
    top_sold = top_sold.sort_values(by='cantidad', ascending=False).head(top_n)

    # Join with Stock Names
    stock_map = {item.id: item.nombre for item in stock}
    top_sold['nombre_producto'] = top_sold['producto_id'].map(stock_map)
    
    # Fill missing names
    top_sold['nombre_producto'] = top_sold['nombre_producto'].fillna('Producto Eliminado')

    return top_sold[['nombre_producto', 'cantidad']]

def get_revenue_trend(ventas: List[Venta]) -> pd.DataFrame:
    """
    Evolución diaria de ventas netas.
    Ya no filtra por días, asume que 'ventas' ya viene filtrado por el controlador principal.
    """
    if not ventas:
        return pd.DataFrame()

    df_ventas = pd.DataFrame([v.dict() for v in ventas])
    df_ventas['fecha'] = pd.to_datetime(df_ventas['fecha'], utc=True).dt.tz_convert(TIMEZONE).dt.date
    
    # Group by date
    trend = df_ventas.groupby('fecha')['total_neto'].sum().reset_index()
    trend = trend.sort_values('fecha')

    return trend

def get_top_clients(ventas: List[Venta], top_n=5) -> pd.DataFrame:
    """
    Top N clientes por gasto total neto.
    """
    if not ventas:
        return pd.DataFrame()

    df_ventas = pd.DataFrame([v.dict() for v in ventas])
    
    top_clients = df_ventas.groupby('cliente')['total_neto'].sum().reset_index()
    top_clients = top_clients.sort_values('total_neto', ascending=False).head(top_n)

    return top_clients

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class StockItem(BaseModel):
    id: int
    codigo: str
    nombre: str
    categoria: str
    cantidad: int
    precio_unitario: float
    min_stock: int = 5
    marca: str

class VentaItem(BaseModel):
    id: int
    venta_id: int
    producto_id: int
    cantidad: int
    precio_unitario: float
    subtotal: float
    marca: str

class Venta(BaseModel):
    id: int
    fecha: datetime
    cliente: str
    total_bruto: float
    descuento_porcentaje: float
    total_neto: float
    marca: str
    estado: str = Field(default="confirmada")
    estado_facturacion: str = Field(default="No Facturado")
    tipo_venta: str = Field(default="Venta Directa")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Concesionario(BaseModel):
    id: int
    nombre_socio: str
    cuit_cuil: Optional[str] = None
    contacto: Optional[str] = None
    marca: str

class ConcesionStock(BaseModel):
    id: int
    concesionario_id: int
    producto_id: int
    marca: str
    cantidad_disponible: int
    fecha_salida: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Cliente(BaseModel):
    id: int
    razon_social: str
    cuit_cuil: Optional[str] = None
    fecha_creacion: Optional[datetime] = None
    marca: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

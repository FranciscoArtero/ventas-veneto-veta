from datetime import timezone, timedelta

# Configuración Regional
TIMEZONE = timezone(timedelta(hours=-3)) # America/Argentina/Buenos_Aires (UTC-3)
TZ_AR = TIMEZONE
IVA_RATE = 0.21

# Constantes de Hojas de Google Sheets
SHEET_STOCK = "STOCK"
SHEET_VENTAS = "VENTAS"
SHEET_VENTAS_ITEMS = "VENTAS_ITEMS"

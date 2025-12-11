from src.services.sqlite_service import init_db, get_connection
from src.services.concesion_service import get_concesionarios, crear_concesionario

def check_db():
    print("Initializing DB...")
    init_db()
    print("DB Initialized.")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check tables
    tables = ['concesionarios', 'concesion_stock']
    for t in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
        if cursor.fetchone():
            print(f"Table '{t}' exists.")
        else:
            print(f"ERROR: Table '{t}' missing.")
            
    # Check column tipo_venta
    cursor.execute("PRAGMA table_info(ventas)")
    cols = [r['name'] for r in cursor.fetchall()]
    if 'tipo_venta' in cols:
        print("Column 'tipo_venta' exists in 'ventas'.")
    else:
        print("ERROR: Column 'tipo_venta' missing in 'ventas'.")
        
    conn.close()

if __name__ == "__main__":
    check_db()
    print("Verification Complete.")

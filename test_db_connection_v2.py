
import psycopg2
import sys

# URL corregida (sin corchetes)
DB_URL = "postgresql://postgres:Lavene2025*@db.jmcwbkxzlpiizbtkspuj.supabase.co:5432/postgres"

def test_connection():
    print(f"Probando conexión a: {DB_URL.split('@')[1]}") # Print host only for privacy
    try:
        conn = psycopg2.connect(DB_URL)
        print("✅ Conexión EXITOSA!")
        conn.close()
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()

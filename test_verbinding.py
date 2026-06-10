from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()
url = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(url)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ref_countries;")
    result = cursor.fetchone()
    print(f"✓ Verbinding gelukt! Aantal landen in database: {result[0]}")
    conn.close()
except Exception as e:
    print(f"✗ Verbindingsfout: {e}")


import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
import psycopg2  # ADDED: PostgreSQL driver for direct polling architecture

# ADDED: Database configuration (same as producer)
DB_NAME = "office_db"
DB_USER = "postgres"
DB_PASSWORD = "postgrespw"
DB_HOST = "localhost"
DB_PORT = 5432

# ADDED: Connect to PostgreSQL
conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
cursor = conn.cursor()

# -------------------------
# Periodically compute average over last 10 minutes
# -------------------------
try:
    while True:
        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        ## Fetch the data from the choosen source (to be implemented)
        # ADDED: Query PostgreSQL directly (simple polling architecture for low-volume data)
        cursor.execute("""
            SELECT AVG(temperature) FROM temperature_readings 
            WHERE recorded_at >= NOW() - INTERVAL '10 minutes'
        """)
        result = cursor.fetchone()
        avg_temp = result[0] if result[0] else None  # ADDED: get actual average from DB
        
        # avg_temp = 0 ## replace with actual values  # COMMENTED: replaced with DB query above
        if avg_temp is not None:
            print(f"{datetime.now()} - Average temperature last 10 minutes: {avg_temp:.2f} °C")
        else:
            print(f"{datetime.now()} - No data in last 10 minutes.")
        time.sleep(600)  # every 10 minutes
except KeyboardInterrupt:
    print("Stopped consuming data.")
finally:
    cursor.close()  # ADDED: cleanup
    conn.close()    # ADDED: cleanup
    print("Exiting.")

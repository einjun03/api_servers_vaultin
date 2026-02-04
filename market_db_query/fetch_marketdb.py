# fetch_marketdb.py
from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

@app.get("/markets")
def get_markets():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        database=os.getenv("POSTGRES_DB"),
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD")
    )
    cursor = conn.cursor()
    cursor.execute("""
        SELECT market_id, market_question, yes_price, no_price, end_date
        FROM current_markets
        ORDER BY end_date
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [
        {
            "id": row[0],
            "question": row[1],
            "yes_price": row[2],
            "no_price": row[3],
            "end_date": row[4].isoformat()
        }
        for row in rows
    ]
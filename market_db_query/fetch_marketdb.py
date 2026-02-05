# fetch_marketdb.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    try:
        cursor.execute("""
            SELECT market_id, market_question, yes_price, no_price, end_date, source
            FROM current_markets
            WHERE source = 'kalshi'
            ORDER BY end_date
        """)
        rows = cursor.fetchall()
    except psycopg2.errors.UndefinedTable:
        return ["table is not ready yet!"]  # Return empty list if table doesn't exist
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [
        {
            "id": row[0],
            "question": row[1],
            "yes_price": row[2],
            "no_price": row[3],
            "end_date": row[4].isoformat(),
            "source": row[5]
        }
        for row in rows
    ]
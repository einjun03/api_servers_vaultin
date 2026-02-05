import psycopg2
from utils import setup_database, fix_timewindow
import os
import requests
from datetime import datetime
import time
import json

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "unknown")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "unknown")
POSTGRES_DB = os.getenv("POSTGRES_DB", "unknown")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "unknown")

#opens a network connection to the database server
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    database=os.getenv("POSTGRES_DB"),
    user="postgres",  # default superuser
    password=os.getenv("POSTGRES_PASSWORD")
)

#define params
limit = 1000
prev_cursor = None
#status = 'open'
max_close_ts = None
min_close_ts = None

completed = False

def get_kalshi_batch():
    """
    gets current batch markets (list)
    """
    global prev_cursor

    #get all entries from curr - the next update time (and hour later)
    try:
        response = requests.get(
            f"https://api.elections.kalshi.com/trade-api/v2/markets",
            params={
                "limit":limit, 
                "cursor": prev_cursor,
                "max_close_ts": max_close_ts,
                "min_close_ts": min_close_ts,
            },
            timeout=5
        )
        response.raise_for_status()  # Raise error for 4xx/5xx
        markets_data = response.json()
        cursor = markets_data["cursor"]
        markets = markets_data["markets"]
    except requests.RequestException as e:
        print(f"API error: {e}")
        time.sleep(30)
        return None
    #update cursor
    prev_cursor = cursor

    #if no cursor then means no more pages left
    if not prev_cursor:
        global completed
        completed = True
    
    #filter to only active markets
    markets_filtered = [m for m in markets if m['status'] == 'active']

    return markets_filtered

def get_all_kalshi():
    global min_close_ts, max_close_ts

    timewindow = fix_timewindow()
    min_close_ts = timewindow['min_close_ts']
    max_close_ts = timewindow['max_close_ts']
    all_markets = []
    while (True):
        #if the previous it was the last page
        if completed:
            break
        #get next batch
        markets = get_kalshi_batch()
        if markets is None:
            #error was raised in last batch- retry (cursor wasnt updated so will auto retry next it)
            continue
        all_markets.extend(markets)
        #print(f"inserted {len(markets)} new entries")
    return all_markets

def format_rows(raw_data, source="kalshi"):
    """
    format kalshi data to db format
    """
        #format data into rows
    rows = []
    for market in raw_data:
        try:
            yes_price = (float(market['yes_bid_dollars']) + float(market['yes_ask_dollars'])) / 2
            no_price = (float(market['no_bid_dollars']) + float(market['no_ask_dollars'])) / 2
            rows.append((
                market["ticker"],
                " ".join([market["title"], market["yes_sub_title"]]),
                market["event_ticker"],
                yes_price,
                no_price,
                datetime.fromisoformat(market['close_time'].replace("Z", "+00:00")),
                " ".join([market["rules_primary"], market["rules_secondary"]]),
                source
            ))
        except Exception as e:
            print(e)
            continue
    return rows

def insert_data(conn, formatted_data):
    #insert polymarket data into the table 

    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO current_markets_all
        (market_id, market_question, event_id, yes_price, no_price, end_date, description, source, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (market_id)
        DO UPDATE SET
            yes_price = EXCLUDED.yes_price,
            no_price = EXCLUDED.no_price,
            updated_at = EXCLUDED.updated_at
    """, formatted_data)

    conn.commit()

    # Cleanup expired markets
    cursor.execute("""
        DELETE FROM current_markets_all
        WHERE end_date < NOW()
    """)
    conn.commit()

    cursor.close()

if __name__ == '__main__':
    #setup database if not already initialized
    setup_database(conn)
    #fetch most recent data
    data = get_all_kalshi()
    cleaned_data = format_rows(data, source="kalshi")
    #update the table with this data 
    insert_data(conn, cleaned_data)
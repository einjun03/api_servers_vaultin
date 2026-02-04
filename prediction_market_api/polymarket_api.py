import psycopg2
from utils import setup_database
import os
import requests
from datetime import datetime, timedelta
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


def get_polymarket_batch(offset, limit=100):
    """
    get a single batch with offset (pagination)
    """
    #get all entries from curr - the next update time (and hour later)
    current_dt = datetime.now()
    max_end_dt = current_dt + timedelta(hours=24)
    try:
        response = requests.get(
            f"https://gamma-api.polymarket.com/events",
            params={
                "active":True, 
                "closed":False, 
                "end_date_min":int(current_dt.timestamp()),
                "end_date_max":int(max_end_dt.timestamp()),
                "limit": limit,
                "offset": offset
            },
            timeout=5
        )
        response.raise_for_status()  # Raise error for 4xx/5xx
    except requests.RequestException as e:
        print(f"API error: {e}")
        time.sleep(30)
        return None
    data = response.json()
    #markets = [obj["title"] for obj in data]
    return data

def get_all_polymarket():
    all_events = []
    curr_offset = 0
    limit = 100
    while(True):
        curr_batch = get_polymarket_batch(offset=curr_offset, limit=limit)
        if curr_batch is None:
            #api error 
            continue
        if not curr_batch:
            #empty batch- done
            break
        all_events.extend(curr_batch)
        curr_offset += limit
    return all_events

def format_rows(raw_data, source="polymarket"):
    """
    format polymarket data to db format
    """
        #format data into rows
    rows = []
    for event in raw_data:
        end_date = event["endDate"]
        event_id = event["id"]
        event_title = event["title"]
        event_slug = event["slug"]
        for market in event['markets']:
            try:
                curr_prices = json.loads(market["outcomePrices"])
                yes_price = curr_prices[0]
                no_price = curr_prices[1]
                rows.append((
                    market["id"],
                    market["question"],
                    market["slug"],
                    event_id,
                    event_title,
                    event_slug,
                    yes_price,
                    no_price,
                    datetime.fromisoformat(end_date.replace("Z", "+00:00")),
                    source
                ))
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
    return rows

def insert_data(conn, formatted_data):
    #insert polymarket data into the table 

    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO current_markets 
        (market_id, market_question, market_slug, event_id, event_title, event_slug, yes_price, no_price, end_date, source, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (market_id)
        DO UPDATE SET
            yes_price = EXCLUDED.yes_price,
            no_price = EXCLUDED.no_price,
            updated_at = EXCLUDED.updated_at
    """, formatted_data)

    conn.commit()

    # Cleanup expired markets
    cursor.execute("""
        DELETE FROM current_markets
        WHERE end_date < NOW()
    """)
    conn.commit()

    cursor.close()


if __name__ == '__main__':
    #setup database if not already initialized
    setup_database(conn)
    #fetch most recent data
    data = get_all_polymarket()
    cleaned_data = format_rows(data, source="polymarket")
    #update the table with this data 
    insert_data(conn, cleaned_data)
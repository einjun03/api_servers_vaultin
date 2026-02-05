
from datetime import datetime, timedelta

def setup_database(conn):
    """
    db keys:
        market_id: polymarket || kalshi
    """
    cursor = conn.cursor()

    #create table active_window (the currently active window of events)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS current_markets (
            market_id VARCHAR(100) PRIMARY KEY,
            market_question TEXT, 
            event_id VARCHAR(100),
            yes_price FLOAT,
            no_price FLOAT,
            end_date TIMESTAMP,
            description TEXT,
            source TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cursor.close()

def to_unix(dt):
    """
    returns unix timestamp as an int
    """
    return int(dt.timestamp())

def fix_timewindow():
    """
    fixes the timewindow we desire to fetch from
    """
    current_dt = datetime.now()
    max_end_dt = current_dt + timedelta(hours=24)
 
    #global min_close_ts
    #global max_close_ts

    res = {}
    res['min_close_ts'] = to_unix(current_dt)
    res['max_close_ts'] = to_unix(max_end_dt)
    return res

    
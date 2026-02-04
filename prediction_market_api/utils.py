
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
            market_slug VARCHAR(200),
            event_id VARCHAR(100),
            event_title TEXT,
            event_slug VARCHAR(200),
            yes_price FLOAT,
            no_price FLOAT,
            end_date TIMESTAMP,
            source TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cursor.close()
    
import sqlite3
import json
import logging

DB_FILE = 'trading_data.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            clientcode TEXT,
            endpoint TEXT,
            data_type TEXT,
            response TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_date DATE DEFAULT CURRENT_DATE,
            clientcode TEXT,
            document_type TEXT,
            filename TEXT,
            content TEXT,
            metadata TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_pnl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            clientcode TEXT,
            total_pnl REAL,
            trades_count INTEGER,
            trades_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS trade_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            clientcode TEXT,
            plan_text TEXT,
            status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("Database initialized")

def store_data(clientcode, endpoint, data_type, response):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            'INSERT INTO api_data (clientcode, endpoint, data_type, response) VALUES (?, ?, ?, ?)',
            (clientcode, endpoint, data_type, json.dumps(response))
        )
        conn.commit()
        conn.close()
        logging.info(f"Stored {data_type} data for {clientcode}")
    except Exception as e:
        logging.error(f"Failed to store data: {e}")

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "pharmacy.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # STRICT: schema ta originală (DOAR 7 coloane)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS medicines_info (
        Med_code TEXT PRIMARY KEY,
        Med_name TEXT NOT NULL,
        Qty INTEGER NOT NULL,
        MRP REAL NOT NULL,
        Mfg TEXT,
        Exp TEXT,
        Purpose TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        full_name TEXT,
        email TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_code TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        sale_price REAL NOT NULL,
        total REAL NOT NULL,
        sale_date TEXT DEFAULT (datetime('now')),
        cashier_id INTEGER
    )
    """)

    # utilizatori demo dacă nu există
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO users (username, password, role, full_name, email)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("admin", "admin123", "admin", "Administrator", "admin@pharmacy.com"),
            ("pharmacist", "pharma123", "pharmacist", "John Pharmacist", "pharma@pharmacy.com"),
            ("cashier", "cash123", "cashier", "Alice Cashier", "cashier@pharmacy.com"),
            ("manager", "manager123", "manager", "Bob Manager", "manager@pharmacy.com"),
        ])

    conn.commit()
    conn.close()

def query_df(sql, params=None):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params or [])
    conn.close()
    return df

def exec_sql(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    rc = cur.rowcount
    conn.close()
    return rc

import sqlite3
import pandas as pd
from typing import Optional
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../cdr_towers.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS towers (
        eci TEXT PRIMARY KEY,
        enb TEXT,
        sector TEXT,
        lat REAL,
        lon REAL,
        azimuth REAL,
        beamwidth REAL,
        last_updated TEXT
    )"""
    )
    return conn


def upsert_towers(df: pd.DataFrame):
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    for _, row in df.iterrows():
        conn.execute(
            """INSERT OR REPLACE INTO towers
            (eci, enb, sector, lat, lon, azimuth, beamwidth, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(row.get("eci", "")),
                str(row.get("enb", "")),
                str(row.get("sector", "")),
                float(row.get("lat", 0)),
                float(row.get("lon", 0)),
                float(row.get("azimuth", 0)),
                float(row.get("beamwidth", 0)),
                now,
            ),
        )
    conn.commit()
    conn.close()


def fetch_towers(search: Optional[str] = None):
    conn = get_connection()
    q = "SELECT * FROM towers"
    params = ()
    if search:
        q += " WHERE eci LIKE ? OR enb LIKE ? OR sector LIKE ?"
        params = (f"%{search}%", f"%{search}%", f"%{search}%")
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df

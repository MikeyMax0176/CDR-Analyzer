import sqlite3
import json
from typing import Any, Dict, List

def get_connection(engine):
    if isinstance(engine, sqlite3.Connection):
        return engine
    return sqlite3.connect(engine)

def init_schema_presets_table(engine):
    conn = get_connection(engine)
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                mapping_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
    return conn

def save_schema_preset(engine, name: str, mapping: Dict[str, Any]):
    conn = init_schema_presets_table(engine)
    mapping_json = json.dumps(mapping)
    with conn:
        conn.execute('''
            INSERT OR REPLACE INTO schema_presets (name, mapping_json)
            VALUES (?, ?)
        ''', (name, mapping_json))

def list_schema_presets(engine) -> List[str]:
    conn = init_schema_presets_table(engine)
    cur = conn.execute('SELECT name FROM schema_presets ORDER BY created_at DESC')
    return [row[0] for row in cur.fetchall()]

def load_schema_preset(engine, name: str) -> Dict[str, Any]:
    conn = init_schema_presets_table(engine)
    cur = conn.execute('SELECT mapping_json FROM schema_presets WHERE name = ?', (name,))
    row = cur.fetchone()
    if row:
        return json.loads(row[0])
    return {}
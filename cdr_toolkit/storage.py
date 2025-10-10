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

# === Case Management System ===

def init_case_schema(engine):
    """Initialize all case management tables"""
    conn = get_connection(engine)
    with conn:
        # Cases table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        
        # Notes table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                title TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        ''')
        
        # Events table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                event_type TEXT,
                title TEXT,
                description TEXT,
                event_time TEXT,
                latitude REAL,
                longitude REAL,
                phone_numbers TEXT,
                tags TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        ''')
        
        # Geofences table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS geofences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                name TEXT,
                coordinates TEXT,
                radius REAL,
                color TEXT DEFAULT '#ff0000',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        ''')
        
        # Pins table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                name TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                icon TEXT DEFAULT 'info-sign',
                color TEXT DEFAULT 'blue',
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        ''')
    return conn

# === Case CRUD Operations ===

def ensure_case(engine, case_name: str, description: str = "") -> int:
    """Create case if it doesn't exist, return case ID"""
    conn = init_case_schema(engine)
    with conn:
        # Try to get existing case
        cur = conn.execute('SELECT id FROM cases WHERE name = ?', (case_name,))
        row = cur.fetchone()
        if row:
            return row[0]
        
        # Create new case
        cur = conn.execute('''
            INSERT INTO cases (name, description) VALUES (?, ?)
        ''', (case_name, description))
        return cur.lastrowid

def list_cases(engine) -> List[Dict[str, Any]]:
    """List all cases"""
    conn = init_case_schema(engine)
    cur = conn.execute('''
        SELECT id, name, description, created_at, updated_at 
        FROM cases ORDER BY updated_at DESC
    ''')
    return [
        {
            'id': row[0],
            'name': row[1], 
            'description': row[2],
            'created_at': row[3],
            'updated_at': row[4]
        }
        for row in cur.fetchall()
    ]

# === Notes CRUD Operations ===

def add_note(engine, case_id: int, title: str, content: str) -> int:
    """Add note to case"""
    conn = get_connection(engine)
    with conn:
        cur = conn.execute('''
            INSERT INTO notes (case_id, title, content) VALUES (?, ?, ?)
        ''', (case_id, title, content))
        
        # Update case timestamp
        conn.execute('''
            UPDATE cases SET updated_at = datetime('now') WHERE id = ?
        ''', (case_id,))
        
        return cur.lastrowid

def list_notes(engine, case_id: int) -> List[Dict[str, Any]]:
    """List notes for a case"""
    conn = get_connection(engine)
    cur = conn.execute('''
        SELECT id, title, content, created_at 
        FROM notes WHERE case_id = ? ORDER BY created_at DESC
    ''', (case_id,))
    return [
        {
            'id': row[0],
            'title': row[1],
            'content': row[2], 
            'created_at': row[3]
        }
        for row in cur.fetchall()
    ]

# === Events CRUD Operations ===

def add_event(engine, case_id: int, event_type: str, title: str, 
              description: str = "", event_time: str = "", 
              latitude: float = None, longitude: float = None,
              phone_numbers: List[str] = None, tags: List[str] = None) -> int:
    """Add event to case"""
    conn = get_connection(engine)
    
    # Convert lists to JSON strings
    phone_numbers_json = json.dumps(phone_numbers or [])
    tags_json = json.dumps(tags or [])
    
    with conn:
        cur = conn.execute('''
            INSERT INTO events (case_id, event_type, title, description, event_time, 
                               latitude, longitude, phone_numbers, tags) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (case_id, event_type, title, description, event_time, 
              latitude, longitude, phone_numbers_json, tags_json))
        
        # Update case timestamp
        conn.execute('''
            UPDATE cases SET updated_at = datetime('now') WHERE id = ?
        ''', (case_id,))
        
        return cur.lastrowid

def list_events(engine, case_id: int = None) -> List[Dict[str, Any]]:
    """List events for a case or all events if case_id is None"""
    conn = get_connection(engine)
    
    if case_id is not None:
        cur = conn.execute('''
            SELECT id, case_id, event_type, title, description, event_time, 
                   latitude, longitude, phone_numbers, tags, created_at
            FROM events WHERE case_id = ? ORDER BY event_time DESC, created_at DESC
        ''', (case_id,))
    else:
        cur = conn.execute('''
            SELECT e.id, e.case_id, e.event_type, e.title, e.description, e.event_time, 
                   e.latitude, e.longitude, e.phone_numbers, e.tags, e.created_at, c.name as case_name
            FROM events e JOIN cases c ON e.case_id = c.id 
            ORDER BY e.event_time DESC, e.created_at DESC
        ''')
    
    events = []
    for row in cur.fetchall():
        event = {
            'id': row[0],
            'case_id': row[1],
            'event_type': row[2],
            'title': row[3],
            'description': row[4],
            'event_time': row[5],
            'latitude': row[6],
            'longitude': row[7],
            'phone_numbers': json.loads(row[8]) if row[8] else [],
            'tags': json.loads(row[9]) if row[9] else [],
            'created_at': row[10]
        }
        if case_id is None and len(row) > 11:
            event['case_name'] = row[11]
        events.append(event)
    
    return events

# === Geofences CRUD Operations ===

def add_geofence(engine, case_id: int, name: str, coordinates: List[List[float]], 
                 radius: float = None, color: str = '#ff0000') -> int:
    """Add geofence to case"""
    conn = get_connection(engine)
    coordinates_json = json.dumps(coordinates)
    
    with conn:
        cur = conn.execute('''
            INSERT INTO geofences (case_id, name, coordinates, radius, color) 
            VALUES (?, ?, ?, ?, ?)
        ''', (case_id, name, coordinates_json, radius, color))
        
        # Update case timestamp
        conn.execute('''
            UPDATE cases SET updated_at = datetime('now') WHERE id = ?
        ''', (case_id,))
        
        return cur.lastrowid

def list_geofences(engine, case_id: int = None) -> List[Dict[str, Any]]:
    """List geofences for a case or all geofences if case_id is None"""
    conn = get_connection(engine)
    
    if case_id is not None:
        cur = conn.execute('''
            SELECT id, name, coordinates, radius, color, created_at
            FROM geofences WHERE case_id = ? ORDER BY created_at DESC
        ''', (case_id,))
    else:
        cur = conn.execute('''
            SELECT g.id, g.case_id, g.name, g.coordinates, g.radius, g.color, g.created_at, c.name as case_name
            FROM geofences g JOIN cases c ON g.case_id = c.id ORDER BY g.created_at DESC
        ''')
    
    geofences = []
    for row in cur.fetchall():
        geofence = {
            'id': row[0],
            'name': row[1] if case_id is not None else row[2],
            'coordinates': json.loads(row[2] if case_id is not None else row[3]),
            'radius': row[3] if case_id is not None else row[4],
            'color': row[4] if case_id is not None else row[5],
            'created_at': row[5] if case_id is not None else row[6]
        }
        if case_id is None:
            geofence['case_id'] = row[1]
            geofence['case_name'] = row[7]
        geofences.append(geofence)
    
    return geofences

# === Pins CRUD Operations ===

def add_pin(engine, case_id: int, name: str, latitude: float, longitude: float,
            icon: str = 'info-sign', color: str = 'blue', description: str = "") -> int:
    """Add pin to case"""
    conn = get_connection(engine)
    
    with conn:
        cur = conn.execute('''
            INSERT INTO pins (case_id, name, latitude, longitude, icon, color, description) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (case_id, name, latitude, longitude, icon, color, description))
        
        # Update case timestamp
        conn.execute('''
            UPDATE cases SET updated_at = datetime('now') WHERE id = ?
        ''', (case_id,))
        
        return cur.lastrowid

def list_pins(engine, case_id: int = None) -> List[Dict[str, Any]]:
    """List pins for a case or all pins if case_id is None"""
    conn = get_connection(engine)
    
    if case_id is not None:
        cur = conn.execute('''
            SELECT id, name, latitude, longitude, icon, color, description, created_at
            FROM pins WHERE case_id = ? ORDER BY created_at DESC
        ''', (case_id,))
    else:
        cur = conn.execute('''
            SELECT p.id, p.case_id, p.name, p.latitude, p.longitude, p.icon, p.color, p.description, p.created_at, c.name as case_name
            FROM pins p JOIN cases c ON p.case_id = c.id ORDER BY p.created_at DESC
        ''')
    
    pins = []
    for row in cur.fetchall():
        pin = {
            'id': row[0],
            'name': row[1] if case_id is not None else row[2],
            'latitude': row[2] if case_id is not None else row[3],
            'longitude': row[3] if case_id is not None else row[4],
            'icon': row[4] if case_id is not None else row[5],
            'color': row[5] if case_id is not None else row[6],
            'description': row[6] if case_id is not None else row[7],
            'created_at': row[7] if case_id is not None else row[8]
        }
        if case_id is None:
            pin['case_id'] = row[1]
            pin['case_name'] = row[9]
        pins.append(pin)
    
    return pins
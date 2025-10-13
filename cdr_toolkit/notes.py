import streamlit as st
import sqlite3
import json
import datetime
from typing import Optional


def get_connection():
    conn = sqlite3.connect("cdr_notes.db", check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER,
        page TEXT,
        context_json TEXT,
        content TEXT,
        author TEXT,
        created_at TEXT,
        updated_at TEXT
    )"""
    )
    return conn


def fetch_notes(case_id: int, page: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, content, author, created_at, updated_at, context_json
        FROM notes
        WHERE case_id=? AND page=?
        ORDER BY created_at DESC, id DESC
    """,
        (case_id, page),
    )
    notes = cur.fetchall()
    conn.close()
    return notes


def add_note(case_id: int, page: str, context: dict, content: str, author: str = "user"):
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (case_id, page, context_json, content, author, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (case_id, page, json.dumps(context), content, author, now, now),
    )
    conn.commit()
    conn.close()


def update_note(note_id: int, content: str):
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE notes SET content=?, updated_at=? WHERE id=?", (content, now, note_id))
    conn.commit()
    conn.close()


def delete_note(note_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()


def render_notes(case_id: Optional[int], page: str, context: dict):
    if not case_id:
        st.info("No active case selected. Notes are disabled.")
        return
    st.markdown("## 📝 Notes")
    notes = fetch_notes(case_id, page)
    for note in notes:
        note_id, content, author, created_at, updated_at, context_json = note
        with st.expander(f"{author} @ {created_at[:19].replace('T',' ')}", expanded=False):
            edited = st.text_area(f"Edit Note {note_id}", value=content, key=f"note_edit_{note_id}")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Update", key=f"update_{note_id}"):
                    update_note(note_id, edited)
                    st.experimental_rerun()
            with col2:
                if st.button("Delete", key=f"delete_{note_id}"):
                    delete_note(note_id)
                    st.experimental_rerun()
            st.caption(f"Context: {context_json}")
    st.markdown("---")
    new_note = st.text_area("Add a new note", key="new_note")
    if st.button("Save Note") and new_note.strip():
        add_note(case_id, page, context, new_note.strip())
        st.success("Note saved!")
        st.experimental_rerun()

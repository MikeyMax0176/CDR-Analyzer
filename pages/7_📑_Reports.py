import streamlit as st
import pandas as pd
import zipfile
import io
import os
from datetime import datetime

st.title("📑 Reports")
from cdr_toolkit.ui import render_snapshot_button

render_snapshot_button()

# --- Artifact selection ---
st.header("Select Artifacts to Include")
artifacts = {
    "Validation summary": True,
    "Top callers": True,
    "Top pairs": True,
    "Network snapshot (HTML)": False,
    "Map snapshot (PNG)": False,
    "Notes export": True,
}
selected = st.multiselect(
    "Artifacts", list(artifacts.keys()), default=[k for k, v in artifacts.items() if v]
)

# --- Prepare outputs ---
outputs = {}

# Validation summary (reuse quality checks)
if "Validation summary" in selected:
    if "active_df" in st.session_state and not st.session_state["active_df"].empty:
        df = st.session_state["active_df"]
        summary = f"Rows: {len(df):,}\nColumns: {len(df.columns)}\n"
        if "call_id" in df.columns:
            summary += f"Duplicate call_id: {df['call_id'].duplicated().sum()}\n"
        outputs["validation_summary.txt"] = summary
    else:
        outputs["validation_summary.txt"] = "No active dataset."

# Top callers
if "Top callers" in selected:
    if (
        "active_df" in st.session_state
        and not st.session_state["active_df"].empty
        and "caller" in st.session_state["active_df"].columns
    ):
        top_callers = st.session_state["active_df"]["caller"].value_counts().head(20)
        outputs["top_callers.csv"] = top_callers.to_csv()
    else:
        outputs["top_callers.csv"] = "No caller data."

# Top pairs
if "Top pairs" in selected:
    if (
        "active_df" in st.session_state
        and not st.session_state["active_df"].empty
        and {"caller", "callee"}.issubset(st.session_state["active_df"].columns)
    ):
        pairs = (
            st.session_state["active_df"]
            .groupby(["caller", "callee"])
            .size()
            .sort_values(ascending=False)
            .head(20)
        )
        outputs["top_pairs.csv"] = pairs.to_csv()
    else:
        outputs["top_pairs.csv"] = "No caller/callee data."

# Network snapshot (HTML)
if "Network snapshot (HTML)" in selected:
    if os.path.exists("cdr_network.html"):
        with open("cdr_network.html", "rb") as f:
            outputs["cdr_network.html"] = f.read()
    else:
        outputs["cdr_network.html"] = b"No network snapshot found."

# Map snapshot (PNG)
if "Map snapshot (PNG)" in selected:
    if os.path.exists("pydeck_map.png"):
        with open("pydeck_map.png", "rb") as f:
            outputs["pydeck_map.png"] = f.read()
    else:
        outputs["pydeck_map.png"] = b"No map snapshot found."

# Notes export
if "Notes export" in selected:
    try:
        import sqlite3

        conn = sqlite3.connect("cdr_notes.db")
        notes = pd.read_sql_query("SELECT * FROM notes", conn)
        outputs["notes_export.csv"] = notes.to_csv(index=False)
        conn.close()
    except Exception as e:
        outputs["notes_export.csv"] = f"Error exporting notes: {e}"

# --- Create zip and download ---
st.header("Download Report Zip")
if st.button("Generate Report Zip"):
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w") as zf:
        for fname, content in outputs.items():
            if isinstance(content, str):
                zf.writestr(fname, content)
            elif isinstance(content, bytes):
                zf.writestr(fname, content)
    mem_zip.seek(0)
    st.download_button(
        "Download Report Zip",
        mem_zip,
        file_name=f"cdr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
    )

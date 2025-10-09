import json
from cdr_toolkit.ingest import read_any, coerce_types
from cdr_toolkit.schemas import CANONICAL_COLUMNS
import streamlit as st
import subprocess
import datetime
if st.button("💾 Save Git Snapshot"):
    try:
        ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        commit_msg = f"snapshot: {ts}"
        result = subprocess.run([
            "git", "add", "-A"
        ], capture_output=True, text=True)
        result2 = subprocess.run([
            "git", "commit", "-m", commit_msg
        ], capture_output=True, text=True)
        result3 = subprocess.run([
            "git", "push"
        ], capture_output=True, text=True)
        if result3.returncode == 0:
            st.success(f"Snapshot saved and pushed! Commit: {commit_msg}")
        elif 'no upstream branch' in result3.stderr:
            # Try to set upstream automatically
            # Get current branch name
            branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
            branch_name = branch.stdout.strip()
            result4 = subprocess.run([
                "git", "push", "--set-upstream", "origin", branch_name
            ], capture_output=True, text=True)
            if result4.returncode == 0:
                st.success(f"Snapshot saved and pushed (set upstream)! Commit: {commit_msg}")
            else:
                st.error(f"Git push (set-upstream) failed: {result4.stderr}")
        elif result2.returncode == 1 and 'nothing to commit' in result2.stderr:
            st.info("No changes to commit.")
        else:
            st.error(f"Git push failed: {result3.stderr}")
    except Exception as e:
        st.error(f"Snapshot failed: {e}")

import streamlit as st
import sqlite3
from cdr_toolkit.storage import save_schema_preset, list_schema_presets, load_schema_preset

# Always initialize mapping in session_state at the very top
if 'mapping' not in st.session_state:
    st.session_state['mapping'] = {}

# Example: replace with your actual DB path or connection
DB_PATH = 'cdr_analyzer.db'


with st.expander("ℹ️ How this page works", expanded=False):
    st.markdown("""
    **CDR Ingest & Mapping Flow**
    1. **Upload your CDR file** (Call Detail Record) using the uploader below. Supported formats: CSV, TSV, TXT.
    2. **Map your columns** to the expected schema (e.g., start_time, caller, callee, duration_sec, CGI/IP, etc.).
    3. **Save your mapping as a preset** for future use, or select an existing preset.
    4. **CGI/IP**: If your CDR contains cell tower (CGI) or IP address columns, you can map them here for advanced analysis later.
    ---
    ### Why Standardize CDRs?
    - **CDRs (Call Detail Records)** from different sources can have different column names, formats, and messy data (like CGI/IP fields).
    - Standardizing means mapping your columns to a common schema (e.g., start_time, caller, callee, duration_sec, CGI, IP).
    - This makes downstream analysis, reporting, and automation much easier and more reliable.
    
    ### What about CGI/IP?
    - **CGI (Cell Global Identity)** and **IP address** columns are often messy or split across multiple fields.
    - Standardizing these lets you do advanced location or network analysis later.
    
    ### Downstream Flow
    1. **Ingest & Map**: Upload and map your CDR columns here.
    2. **Preview & Quality Check**: See your data, check for errors, and get feedback.
    3. **Analysis & Export**: Use the cleaned, standardized data for further analysis or export.
    """)
st.header("Ingest & Map Schema")

# --- Preset selection ---
presets = list_schema_presets(DB_PATH)
selected_preset = st.selectbox(
    "Choose a schema preset",
    presets,
    help="Select a saved mapping preset to auto-fill the mapping fields."
)

# --- File uploader with help tooltip ---
uploaded = st.file_uploader(
    "Upload CDR (CSV/TSV/TXT)",
    type=["csv", "tsv", "txt"],
    help="Upload your CDR file here. Supported formats: CSV, TSV, TXT."
)

 # --- Mapping input (simulate with a text area for now) ---
if selected_preset:
    preset_mapping = load_schema_preset(DB_PATH, selected_preset)
    if preset_mapping:
        st.session_state['mapping'] = preset_mapping

mapping_json = st.text_area(
    "Edit mapping (JSON)",
    value=str(st.session_state.get('mapping', {})),
    help="Paste or edit your column mapping here as a JSON dictionary. Example: {'start_time': 'Start', 'caller': 'From', 'callee': 'To', 'CGI': 'CellTower', 'IP': 'IPAddress'}"
)

# --- Apply mapping button ---
if uploaded and st.button("✔️ Apply mapping"):
    try:
        try:
            mapping = json.loads(mapping_json)
        except Exception as e:
            st.error(f"Invalid JSON mapping: {e}")
            mapping = None
        if mapping is not None:
            uploaded.seek(0)
            raw = read_any(uploaded)
            # Drop index-like columns
            drop_cols = [c for c in raw.columns if c in ("Unnamed: 0", "index") or c.startswith("Unnamed:")]
            if drop_cols:
                raw = raw.drop(columns=drop_cols)
            if not mapping:
                # Auto identity-map for canonical columns present
                mapping = {col: col for col in CANONICAL_COLUMNS if col in raw.columns}
                st.info("Auto-mapped columns:")
                st.json(mapping)
            canon = coerce_types(raw, mapping)
            if "datasets" not in st.session_state:
                st.session_state["datasets"] = {}
            st.session_state["datasets"][uploaded.name] = canon
            st.success(f"Mapping applied and dataset '{uploaded.name}' saved!")
            st.dataframe(canon.head(50), use_container_width=True)
    except Exception as e:
        st.error(f"Failed to apply mapping: {e}")

# --- Save preset ---
preset_name = st.text_input("Preset name")
if st.button("Save as preset"):
    try:
        mapping = eval(mapping_json) if mapping_json else {}
        save_schema_preset(DB_PATH, preset_name, mapping)
        st.success(f"Preset '{preset_name}' saved!")
    except Exception as e:
        st.error(f"Error saving preset: {e}")

# --- Show current mapping ---
st.write("Current mapping:", st.session_state['mapping'])


import streamlit as st
import sqlite3
from cdr_toolkit.storage import save_schema_preset, list_schema_presets, load_schema_preset

# Always initialize mapping in session_state at the very top
if 'mapping' not in st.session_state:
    st.session_state['mapping'] = {}

# Example: replace with your actual DB path or connection
DB_PATH = 'cdr_analyzer.db'


with st.popover("ℹ️ How this works"):
    st.markdown("""
    **CDR Ingest & Mapping Flow**
    1. **Upload your CDR file** (Call Detail Record) using the uploader below. Supported formats: CSV, TSV, TXT.
    2. **Map your columns** to the expected schema (e.g., start_time, caller, callee, duration_sec, CGI/IP, etc.).
    3. **Save your mapping as a preset** for future use, or select an existing preset.
    4. **CGI/IP**: If your CDR contains cell tower (CGI) or IP address columns, you can map them here for advanced analysis later.
    """)

# --- Info Modal ---
if 'show_info_modal' not in st.session_state:
    st.session_state['show_info_modal'] = False

if st.button("ℹ️ Info"):
    st.session_state['show_info_modal'] = True

if st.session_state['show_info_modal']:
    with st.modal("About messy CDRs, standardization, and the flow"):
        st.markdown("""
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
        if st.button("Got it"):
            st.session_state['show_info_modal'] = False
st.header("Ingest & Map Schema")

# --- Preset selection ---
presets = list_schema_presets(DB_PATH)
selected_preset = st.selectbox(
    "Choose a schema preset",
    presets,
    help="Select a saved mapping preset to auto-fill the mapping fields."
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

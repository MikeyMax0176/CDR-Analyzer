import streamlit as st
import sqlite3
from cdr_toolkit.storage import save_schema_preset, list_schema_presets, load_schema_preset

# Example: replace with your actual DB path or connection
DB_PATH = 'cdr_analyzer.db'

st.header("Ingest & Map Schema")

# --- Preset selection ---
presets = list_schema_presets(DB_PATH)
selected_preset = st.selectbox("Choose a schema preset", presets)

# --- Mapping input (simulate with a text area for now) ---
if 'mapping' not in st.session_state:
    st.session_state['mapping'] = {}

if selected_preset:
    preset_mapping = load_schema_preset(DB_PATH, selected_preset)
    if preset_mapping:
        st.session_state['mapping'] = preset_mapping

mapping_json = st.text_area("Edit mapping (JSON)", value=str(st.session_state['mapping']))

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

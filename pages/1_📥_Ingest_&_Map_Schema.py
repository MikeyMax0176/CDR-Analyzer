import streamlit as st
import pandas as pd
import io
import difflib
import re
from datetime import datetime
from cdr_toolkit.storage import save_schema_preset, list_schema_presets, load_schema_preset

st.title("📥 Ingest & Map Schema")

st.markdown(
    """
Upload your CDR files and map columns to the standard schema for analysis.
You can save and reuse column mappings as presets.
"""
)

# Canonical columns
CANONICAL_COLUMNS = [
    "start_time", "caller", "callee", "duration_sec", "ip_src", "ip_dst", 
    "cgi", "imei", "imsi", "latitude", "longitude", "call_type", "direction", "technology"
]

# Synonyms dictionary for fuzzy matching
COLUMN_SYNONYMS = {
    "start_time": ["timestamp", "datetime", "call_time", "start", "time", "date_time"],
    "caller": ["calling_party", "a_number", "from_number", "source_number", "msisdn_a"],
    "callee": ["called_party", "b_number", "to_number", "dest_number", "msisdn_b"],
    "duration_sec": ["duration", "call_duration", "length", "time_duration", "seconds"],
    "ip_src": ["source_ip", "src_ip", "ip_source", "origin_ip"],
    "ip_dst": ["dest_ip", "dst_ip", "ip_dest", "target_ip"],
    "cgi": ["cell_id", "tower_id", "site_id", "cell", "tower", "bts"],
    "imei": ["device_id", "equipment_id", "mobile_id"],
    "imsi": ["subscriber_id", "sim_id", "user_id"],
    "latitude": ["lat", "y_coord", "north"],
    "longitude": ["lon", "lng", "x_coord", "east"],
    "call_type": ["type", "service", "category", "voice", "sms", "data"],
    "direction": ["dir", "call_dir", "incoming", "outgoing", "in_out"],
    "technology": ["tech", "network", "2g", "3g", "4g", "5g", "gsm", "umts", "lte"]
}


def read_uploaded_table(uploaded_file):
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(uploaded_file.read()))
        else:
            sample = uploaded_file.read(4096).decode("utf-8", errors="ignore")
            tab_count = sample.count("\t")
            comma_count = sample.count(",")
            semicolon_count = sample.count(";")
            if tab_count > comma_count and tab_count > semicolon_count:
                sep = "\t"
            elif semicolon_count > comma_count:
                sep = ";"
            else:
                sep = ","
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=sep, low_memory=False)
        return df, None
    except Exception as e:
        return None, str(e)


def suggest_mapping(df_columns):
    """Suggest column mappings using synonyms and fuzzy matching"""
    mapping = {}
    used_columns = set()
    
    for canonical_col in CANONICAL_COLUMNS:
        best_match = None
        best_score = 0
        
        # Check synonyms first
        synonyms = COLUMN_SYNONYMS.get(canonical_col, [])
        all_candidates = [canonical_col] + synonyms
        
        for df_col in df_columns:
            if df_col in used_columns:
                continue
                
            df_col_lower = df_col.lower().strip()
            
            # Exact match
            if df_col_lower in [c.lower() for c in all_candidates]:
                best_match = df_col
                best_score = 100
                break
                
            # Fuzzy match
            for candidate in all_candidates:
                ratio = difflib.SequenceMatcher(None, df_col_lower, candidate.lower()).ratio()
                if ratio > best_score and ratio > 0.6:
                    best_score = ratio
                    best_match = df_col
                    
            # Regex patterns
            patterns = {
                "start_time": r".*(time|date).*",
                "caller": r".*(caller|calling|from|source|a_num).*",
                "callee": r".*(callee|called|to|dest|b_num).*",
                "duration_sec": r".*(duration|length|time).*",
                "latitude": r".*(lat).*",
                "longitude": r".*(lon|lng).*",
                "imei": r".*(imei).*",
                "imsi": r".*(imsi).*"
            }
            
            if canonical_col in patterns:
                if re.match(patterns[canonical_col], df_col_lower) and best_score < 0.8:
                    best_score = 0.8
                    best_match = df_col
        
        if best_match and best_score > 0.6:
            mapping[canonical_col] = best_match
            used_columns.add(best_match)
    
    return mapping


def coerce_types(df, mapping):
    """Coerce columns to appropriate types"""
    result_df = pd.DataFrame()
    
    for canonical_col, original_col in mapping.items():
        if original_col not in df.columns:
            continue
            
        series = df[original_col].copy()
        
        try:
            if canonical_col == "start_time":
                series = pd.to_datetime(series, errors='coerce')
            elif canonical_col in ["duration_sec"]:
                series = pd.to_numeric(series, errors='coerce').astype('Int64')
            elif canonical_col in ["latitude", "longitude"]:
                series = pd.to_numeric(series, errors='coerce')
            else:
                series = series.astype(str)
                
            result_df[canonical_col] = series
        except Exception:
            result_df[canonical_col] = series
    
    return result_df


# Initialize session state
if "datasets" not in st.session_state:
    st.session_state.datasets = {}
if "mapping" not in st.session_state:
    st.session_state.mapping = {}

# File upload
uploaded_file = st.file_uploader(
    "Upload CDR file (CSV, TSV, XLSX, TXT)", type=["csv", "tsv", "txt", "xlsx", "xls"]
)

if uploaded_file:
    df, err = read_uploaded_table(uploaded_file)
    if err is None:
        st.success(f"Loaded {len(df):,} rows, {len(df.columns)} columns.")
        st.dataframe(df.head(10), use_container_width=True)
        
        # Mapping section
        st.subheader("🔗 Column Mapping")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🤖 Suggest Mapping"):
                suggested = suggest_mapping(df.columns.tolist())
                st.session_state.mapping = suggested
                st.success(f"Suggested mapping for {len(suggested)} columns")
        
        with col2:
            # Preset management
            try:
                presets = list_schema_presets(st.session_state.get('engine', 'cdr_toolkit.db'))
                if presets:
                    selected_preset = st.selectbox("Load preset", [""] + presets)
                    if selected_preset and st.button("Load Preset"):
                        preset_mapping = load_schema_preset(st.session_state.get('engine', 'cdr_toolkit.db'), selected_preset)
                        st.session_state.mapping = preset_mapping
                        st.success(f"Loaded preset: {selected_preset}")
            except Exception:
                st.info("Presets not available")
        
        # Mapping UI
        st.markdown("**Map columns to canonical schema:**")
        mapping = {}
        
        for canonical_col in CANONICAL_COLUMNS:
            suggested_col = st.session_state.mapping.get(canonical_col, "")
            options = [""] + df.columns.tolist()
            
            if suggested_col in options:
                default_idx = options.index(suggested_col)
            else:
                default_idx = 0
                
            selected = st.selectbox(
                f"{canonical_col}",
                options,
                index=default_idx,
                key=f"map_{canonical_col}"
            )
            
            if selected:
                mapping[canonical_col] = selected
        
        # Apply mapping
        if mapping and st.button("✅ Apply Mapping"):
            try:
                canonical_df = coerce_types(df, mapping)
                dataset_name = uploaded_file.name
                
                # Store both raw and canonical
                st.session_state.datasets[dataset_name] = canonical_df
                st.session_state["active_df"] = canonical_df
                
                st.success(f"✅ Applied mapping! Created canonical dataset with {len(canonical_df):,} rows, {len(canonical_df.columns)} columns.")
                
                # Show preview
                st.subheader("📋 Canonical Data Preview")
                st.dataframe(canonical_df.head(10), use_container_width=True)
                
                # Save preset option
                preset_name = st.text_input("Save mapping as preset (optional)")
                if preset_name and st.button("💾 Save Preset"):
                    try:
                        save_schema_preset(st.session_state.get('engine', 'cdr_toolkit.db'), preset_name, mapping)
                        st.success(f"Saved preset: {preset_name}")
                    except Exception as e:
                        st.error(f"Failed to save preset: {e}")
                        
            except Exception as e:
                st.error(f"Failed to apply mapping: {e}")
    else:
        st.error(f"Failed to load file: {err}")

# Show current datasets
if st.session_state.datasets:
    st.subheader("📊 Current Session Datasets")
    
    for name, df in st.session_state.datasets.items():
        with st.expander(f"Dataset: {name} ({len(df):,} rows)"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                if st.button(f"Remove {name}", key=f"remove_{name}"):
                    del st.session_state.datasets[name]
                    st.rerun()
            
            st.dataframe(df.head(10), use_container_width=True)
else:
    st.info("👆 Upload a file to get started with CDR analysis")

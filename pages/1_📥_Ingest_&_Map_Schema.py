import streamlit as st
import pandas as pd
import io
from cdr_toolkit.ingest import validate_cdr, coerce_types
from cdr_toolkit.storage import save_schema_preset, list_schema_presets, load_schema_preset

st.set_page_config(page_title="Ingest & Map Schema", page_icon="📥", layout="wide")
st.title("📥 Ingest & Map Schema")

st.markdown("""
Upload your CDR files and map columns to the standard schema for analysis.
You can save and reuse column mappings as presets.
""")

# Helper function to get proper column configuration for CDR dataframes
def get_cdr_column_config(df):
    """
    Get column configuration for CDR dataframes to ensure proper display formatting
    """
    column_config = {}
    
    # Text columns for identifiers
    id_columns = ['caller', 'callee', 'imei', 'imsi', 'cell_id', 'lac', 'call_id']
    for col in id_columns:
        if col in df.columns:
            column_config[col] = st.column_config.TextColumn(
                col.upper(),
                help=f"{col.upper()} identifier",
                max_chars=20,
            )
    
    # Number columns with specific formatting
    if 'duration' in df.columns:
        column_config['duration'] = st.column_config.NumberColumn(
            "DURATION",
            help="Call duration in seconds",
            format="%.0f"
        )
    
    if 'latitude' in df.columns:
        column_config['latitude'] = st.column_config.NumberColumn(
            "LATITUDE", 
            help="GPS latitude coordinate",
            format="%.6f"
        )
    
    if 'longitude' in df.columns:
        column_config['longitude'] = st.column_config.NumberColumn(
            "LONGITUDE",
            help="GPS longitude coordinate", 
            format="%.6f"
        )
    
    return column_config

def display_cdr_dataframe(df, max_rows=20, use_container_width=True):
    """
    Display CDR dataframe with proper column configuration
    """
    column_config = get_cdr_column_config(df)
    
    st.dataframe(
        df.head(max_rows), 
        use_container_width=use_container_width,
        column_config=column_config,
        hide_index=True
    )

# Helper function to detect separator
def best_sep(sample: str):
    lines = sample.split('\n')[:5]
    comma_count = sum(line.count(',') for line in lines) / max(len(lines), 1)
    tab_count = sum(line.count('\t') for line in lines) / max(len(lines), 1)
    semicolon_count = sum(line.count(';') for line in lines) / max(len(lines), 1)
    
    if tab_count > comma_count and tab_count > semicolon_count:
        return '\t'
    elif semicolon_count > comma_count:
        return ';'
    else:
        return ','

# AI mapping function
def ai_map_columns(df_columns, sample_data=None):
    """
    Intelligently map columns to standard CDR schema based on column names and data patterns
    """
    import re
    
    # Define patterns for each standard field
    mapping_patterns = {
        'caller': [
            r'.*caller.*', r'.*calling.*', r'.*a[-_]?number.*', r'.*a[-_]?party.*',
            r'.*from.*', r'.*source.*', r'.*originator.*', r'.*msisdn.*a.*'
        ],
        'callee': [
            r'.*callee.*', r'.*called.*', r'.*b[-_]?number.*', r'.*b[-_]?party.*',
            r'.*to.*', r'.*dest.*', r'.*target.*', r'.*msisdn.*b.*'
        ],
        'start_time': [
            r'.*start.*time.*', r'.*begin.*', r'.*timestamp.*', r'.*date.*time.*',
            r'.*call.*time.*', r'.*time.*start.*', r'.*datetime.*'
        ],
        'duration': [
            r'.*duration.*', r'.*length.*', r'.*time.*', r'.*seconds.*',
            r'.*minutes.*', r'.*call.*time.*', r'.*elapsed.*'
        ],
        'call_type': [
            r'.*call.*type.*', r'.*type.*', r'.*service.*', r'.*category.*',
            r'.*voice.*', r'.*sms.*', r'.*data.*'
        ],
        'cell_id': [
            r'.*cell.*id.*', r'.*cell.*', r'.*tower.*', r'.*site.*',
            r'.*base.*station.*', r'.*bts.*', r'.*ci.*'
        ],
        'lac': [
            r'.*lac.*', r'.*location.*area.*', r'.*area.*code.*'
        ],
        'imei': [
            r'.*imei.*', r'.*device.*id.*', r'.*equipment.*id.*'
        ],
        'imsi': [
            r'.*imsi.*', r'.*subscriber.*id.*', r'.*sim.*id.*'
        ],
        'direction': [
            r'.*direction.*', r'.*in.*out.*', r'.*incoming.*', r'.*outgoing.*',
            r'.*originating.*', r'.*terminating.*'
        ],
        'technology': [
            r'.*tech.*', r'.*network.*', r'.*2g.*', r'.*3g.*', r'.*4g.*', r'.*5g.*',
            r'.*gsm.*', r'.*umts.*', r'.*lte.*'
        ],
        'latitude': [
            r'.*lat.*', r'.*latitude.*', r'.*y.*coord.*', r'.*north.*'
        ],
        'longitude': [
            r'.*lon.*', r'.*lng.*', r'.*longitude.*', r'.*x.*coord.*', r'.*east.*'
        ]
    }
    
    # Score each column against each pattern
    suggested_mapping = {}
    used_columns = set()
    
    for standard_field, patterns in mapping_patterns.items():
        best_score = 0
        best_column = None
        
        for column in df_columns:
            if column in used_columns:
                continue
                
            column_lower = column.lower()
            score = 0
            
            # Check pattern matches
            for pattern in patterns:
                if re.match(pattern, column_lower):
                    score += 10
                elif any(word in column_lower for word in pattern.replace('.*', '').split('[-_]?')):
                    score += 5
            
            # Bonus for exact/common matches
            exact_matches = {
                'caller': ['caller', 'calling_party', 'a_number', 'from_number'],
                'callee': ['callee', 'called_party', 'b_number', 'to_number'],
                'start_time': ['start_time', 'timestamp', 'datetime', 'call_time'],
                'duration': ['duration', 'call_duration', 'length'],
                'cell_id': ['cell_id', 'cell', 'tower_id', 'site_id']
            }
            
            if standard_field in exact_matches:
                if column_lower in exact_matches[standard_field]:
                    score += 20
            
            # Additional data-based scoring if sample data is provided
            if sample_data is not None and column in sample_data.columns:
                sample_values = sample_data[column].dropna().astype(str).head(100)
                
                if standard_field == 'caller' or standard_field == 'callee':
                    # Check for phone number patterns
                    phone_like = sum(1 for val in sample_values if re.match(r'^\+?[\d\s\-\(\)]{7,15}$', val))
                    if phone_like / len(sample_values) > 0.7:
                        score += 15
                
                elif standard_field == 'start_time':
                    # Check for timestamp patterns
                    time_like = sum(1 for val in sample_values if 
                                  any(char in val for char in ['-', ':', '/', ' ']) and 
                                  any(char.isdigit() for char in val))
                    if time_like / len(sample_values) > 0.7:
                        score += 15
                
                elif standard_field == 'duration':
                    # Check for numeric values
                    try:
                        numeric_vals = pd.to_numeric(sample_values, errors='coerce').dropna()
                        if len(numeric_vals) / len(sample_values) > 0.8:
                            score += 10
                    except:
                        pass
                
                elif standard_field == 'cell_id':
                    # Check for numeric/hex patterns
                    numeric_like = sum(1 for val in sample_values if 
                                     val.isdigit() or re.match(r'^[0-9a-fA-F]+$', val))
                    if numeric_like / len(sample_values) > 0.8:
                        score += 10
            
            if score > best_score:
                best_score = score
                best_column = column
        
        # Only suggest if we have a reasonable confidence
        if best_score >= 10 and best_column:
            suggested_mapping[standard_field] = best_column
            used_columns.add(best_column)
    
    return suggested_mapping

# Initialize session state
if 'datasets' not in st.session_state:
    st.session_state.datasets = {}

# File uploader
uploaded_file = st.file_uploader(
    "Upload CDR file", 
    type=['csv', 'tsv', 'txt'],
    help="Upload CSV, TSV, or TXT files containing CDR data"
)

if uploaded_file:
    # Read sample to detect separator
    sample = uploaded_file.read(4096).decode("utf-8", errors="ignore")
    sep = best_sep(sample)
    uploaded_file.seek(0)
    
    try:
        # Load the dataframe
        df = pd.read_csv(uploaded_file, sep=sep, low_memory=False)
        
        sep_label = {"\t": "TAB", ",": "COMMA", ";": "SEMICOLON", "|": "PIPE"}.get(sep, repr(sep))
        st.success(f"✅ Loaded {len(df):,} rows with {len(df.columns)} columns (detected {sep_label} separator)")
        
        # Show preview
        st.subheader("📋 Data Preview")
        # Use column configuration for raw data preview too
        column_config = get_cdr_column_config(df)
        st.dataframe(df.head(100), use_container_width=True, column_config=column_config, hide_index=True)
        
        # Column mapping section
        st.subheader("🔗 Column Mapping")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # AI mapping section
            col_ai, col_clear, col_manual = st.columns([1, 1, 2])
            with col_ai:
                if st.button("🤖 AI Auto-Map", help="Use AI to automatically suggest column mappings"):
                    # Get AI suggestions
                    ai_mapping = ai_map_columns(df.columns, df.head(100))
                    
                    # Update session state with suggestions
                    for field, column in ai_mapping.items():
                        st.session_state[f"map_{field}"] = column
                    
                    st.success(f"🎯 AI mapped {len(ai_mapping)} fields!")
                    if ai_mapping:
                        st.info("📋 Mapped: " + ", ".join([f"{k}→{v}" for k, v in ai_mapping.items()]))
                    st.rerun()
            
            with col_clear:
                if st.button("🧹 Clear All", help="Clear all column mappings"):
                    # Clear all mapping session state
                    for field in ['caller', 'callee', 'start_time', 'duration', 'call_type', 
                                 'cell_id', 'lac', 'imei', 'imsi', 'direction', 'technology', 
                                 'latitude', 'longitude']:
                        if f"map_{field}" in st.session_state:
                            st.session_state[f"map_{field}"] = ""
                    st.success("🧹 Cleared all mappings!")
                    st.rerun()
            
            with col_manual:
                st.markdown("**Map your columns to standard CDR schema:**")
            
            # AI Preview Section (show suggestions without applying them)
            with st.expander("🔮 Preview AI Mapping Suggestions", expanded=False):
                ai_preview = ai_map_columns(df.columns, df.head(100))
                if ai_preview:
                    st.markdown("**AI suggests these mappings:**")
                    for standard_field, suggested_column in ai_preview.items():
                        col_field, col_arrow, col_suggestion = st.columns([1, 0.2, 1])
                        with col_field:
                            st.code(standard_field)
                        with col_arrow:
                            st.markdown("→")
                        with col_suggestion:
                            st.code(suggested_column)
                    
                    if st.button("✅ Apply AI Suggestions", key="apply_ai_preview"):
                        for field, column in ai_preview.items():
                            st.session_state[f"map_{field}"] = column
                        st.success(f"Applied {len(ai_preview)} AI suggestions!")
                        st.rerun()
                else:
                    st.info("🤷 AI couldn't find confident mappings for your columns. Try manual mapping below.")
            
            # Standard CDR schema fields
            standard_fields = {
                'caller': 'Calling party number (A-number)',
                'callee': 'Called party number (B-number)', 
                'start_time': 'Call start timestamp',
                'duration': 'Call duration in seconds',
                'call_type': 'Call type (voice, sms, data)',
                'cell_id': 'Cell ID or tower identifier',
                'lac': 'Location Area Code',
                'imei': 'Device IMEI',
                'imsi': 'Subscriber IMSI',
                'direction': 'Call direction (inbound/outbound)',
                'technology': 'Network technology (2G/3G/4G/5G)',
                'latitude': 'GPS latitude',
                'longitude': 'GPS longitude'
            }
            
            # Create mapping form
            mapping = {}
            available_columns = [''] + list(df.columns)
            
            for field, description in standard_fields.items():
                col_map, col_desc = st.columns([1, 2])
                with col_map:
                    selected_col = st.selectbox(
                        f"{field}",
                        available_columns,
                        key=f"map_{field}",
                        help=description
                    )
                    if selected_col:
                        mapping[field] = selected_col
                with col_desc:
                    st.caption(description)
        
        with col2:
            st.markdown("**Schema Presets**")
            
            # Load preset
            presets = list_schema_presets(st.session_state.get('engine', 'cdr_toolkit.db'))
            if presets:
                selected_preset = st.selectbox("Load preset", [''] + presets)
                if selected_preset and st.button("Load Preset"):
                    preset_mapping = load_schema_preset(st.session_state.get('engine', 'cdr_toolkit.db'), selected_preset)
                    # Update the form fields
                    for field, column in preset_mapping.items():
                        if f"map_{field}" in st.session_state:
                            st.session_state[f"map_{field}"] = column
                    st.success(f"Loaded preset: {selected_preset}")
                    st.rerun()
            
            # Save preset
            st.markdown("**Save Current Mapping**")
            preset_name = st.text_input("Preset name", placeholder="My CDR Schema")
            if st.button("Save Preset") and preset_name and mapping:
                save_schema_preset(st.session_state.get('engine', 'cdr_toolkit.db'), preset_name, mapping)
                st.success(f"Saved preset: {preset_name}")
                st.rerun()
        
        # Process and validate
        if mapping:
            st.subheader("🔄 Process Data")
            
            col1, col2 = st.columns(2)
            with col1:
                dataset_name = st.text_input("Dataset name", value=f"Dataset_{len(st.session_state.datasets)+1}")
            with col2:
                if st.button("Process & Add to Session", type="primary"):
                    try:
                        # Apply column mapping using coerce_types
                        processed_df = coerce_types(df, mapping)
                        
                        # Validate the processed data
                        validation_result = validate_cdr(processed_df)
                        
                        # Store in session
                        st.session_state.datasets[dataset_name] = processed_df
                        
                        # Show results
                        if validation_result["errors"]:
                            st.warning(f"⚠️ Added dataset with {len(validation_result['errors'])} validation errors")
                            for error in validation_result["errors"]:
                                st.error(error)
                        else:
                            st.success(f"✅ Successfully added dataset: {dataset_name}")
                        
                        if validation_result["warnings"]:
                            for warning in validation_result["warnings"]:
                                st.warning(warning)
                        
                        # Show mapping summary
                        st.markdown("**Applied Mapping:**")
                        for standard_field, original_column in mapping.items():
                            st.markdown(f"- `{standard_field}` ← `{original_column}`")
                        
                    except Exception as e:
                        st.error(f"❌ Error processing data: {e}")
            
            # Show validation preview
            if mapping:
                st.subheader("✅ Validation Preview")
                
                # Create preview with mapped columns using coerce_types
                preview_df = coerce_types(df, mapping)
                
                # Show only mapped columns
                mapped_columns = list(mapping.keys())
                if mapped_columns:
                    preview_mapped = preview_df[mapped_columns]
                    # Use proper display function for CDR data
                    display_cdr_dataframe(preview_mapped, max_rows=20)
                    
                    # Quick validation
                    validation_result = validate_cdr(preview_mapped)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Errors", len(validation_result["errors"]))
                    with col2:
                        st.metric("Warnings", len(validation_result["warnings"]))
                    with col3:
                        st.metric("Mapped Fields", len(mapping))
        
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        st.info("Please check your file format and try again.")

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
            
            # Use proper display function for CDR data
            display_cdr_dataframe(df, max_rows=10)
else:
    st.info("👆 Upload a file to get started with CDR analysis")

# Footer
st.markdown("---")
st.markdown("""
**💡 Tips:**
- **🤖 AI Auto-Map**: Use AI to automatically suggest column mappings based on names and data patterns
- **🔮 Preview Suggestions**: Check AI suggestions before applying them to ensure accuracy
- **Standard Fields**: Map your columns to standard CDR fields for consistent analysis
- **Save Presets**: Save column mappings to reuse with similar datasets
- **Multiple Datasets**: You can load multiple datasets and combine them later
- **Validation**: Check for common data quality issues before analysis
""")

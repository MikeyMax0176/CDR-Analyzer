import streamlit as st
import pandas as pd
from cdr_toolkit.ingest import validate_cdr

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

st.header("Preview & Quality Checks")

# Prefer active_df if available, otherwise use dataset selection
if 'active_df' in st.session_state and not st.session_state['active_df'].empty:
    df = st.session_state['active_df']
    st.success(f"📊 Using combined filtered dataset ({len(df):,} rows from {df['source'].nunique() if 'source' in df.columns else 1} source(s))")
    
    # Show source distribution if multiple sources
    if 'source' in df.columns and df['source'].nunique() > 1:
        source_counts = df['source'].value_counts()
        st.markdown("**Quality check across data sources:**")
        for source, count in source_counts.items():
            color = st.session_state.get('filters', {}).get('colors', {}).get(source, '#1f77b4')
            st.markdown(f"<span style='color: {color}'>●</span> {source}: {count:,} records", unsafe_allow_html=True)
else:
    datasets = st.session_state.get("datasets", {})
    if not datasets:
        st.info("No datasets loaded in session. Please ingest data first.")
        st.stop()

    dataset_name = st.selectbox("Select dataset", list(datasets.keys()))
    df = datasets[dataset_name]
    st.info("💡 Tip: Use 'Datasets & Filters' page to create a combined filtered dataset for enhanced analysis.")

column_config = get_cdr_column_config(df)
st.dataframe(df.head(200), use_container_width=True, column_config=column_config, hide_index=True)

result = validate_cdr(df)

if result["errors"]:
    for err in result["errors"]:
        st.error(err)
else:
    st.success("No errors found!")

for warn in result["warnings"]:
    st.warning(warn)

st.subheader("Summary Table (dtype and null rate)")
st.dataframe(result["summary"])

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from cdr_toolkit.filters import apply_filters, get_dataset_summary, get_top_numbers
import plotly.express as px
import plotly.graph_objects as go

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

st.set_page_config(page_title="Datasets & Filters", page_icon="🗃️", layout="wide")
st.title("🗃️ Datasets & Filters")

# Initialize session state for filters
if 'filters' not in st.session_state:
    st.session_state.filters = {
        'enabled_sources': [],
        'colors': {},
        'mute_numbers': [],
        'time_range': None,
        'min_duration': 0,
        'tech_sel': []
    }

# Get available datasets
datasets = {}
if 'datasets' in st.session_state:
    datasets = st.session_state.datasets

if not datasets:
    st.warning("⚠️ No datasets loaded. Please upload and map datasets in the 'Ingest & Map Schema' page first.")
    st.stop()

# Sidebar - Global Filters
with st.sidebar:
    st.header("🎛️ Global Filters")
    
    # Time Range Filter
    st.subheader("📅 Time Range")
    
    # Get overall date range from all datasets
    all_dates = []
    for df in datasets.values():
        if 'start_time' in df.columns:
            try:
                dates = pd.to_datetime(df['start_time'], errors='coerce').dropna()
                if not dates.empty:
                    all_dates.extend([dates.min(), dates.max()])
            except:
                pass
    
    if all_dates:
        min_date = min(all_dates).date()
        max_date = max(all_dates).date()
        
        use_time_filter = st.checkbox("Enable time filter", value=False)
        if use_time_filter:
            date_range = st.date_input(
                "Date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            if len(date_range) == 2:
                start_dt = datetime.combine(date_range[0], datetime.min.time())
                end_dt = datetime.combine(date_range[1], datetime.max.time())
                st.session_state.filters['time_range'] = (start_dt, end_dt)
            else:
                st.session_state.filters['time_range'] = None
        else:
            st.session_state.filters['time_range'] = None
    else:
        st.info("No timestamp data found in datasets")
        st.session_state.filters['time_range'] = None
    
    # Duration Filter
    st.subheader("⏱️ Duration Filter")
    min_duration = st.number_input(
        "Minimum duration (seconds)", 
        min_value=0.0, 
        value=0.0, 
        step=1.0,
        help="Filter out calls shorter than this duration"
    )
    st.session_state.filters['min_duration'] = min_duration
    
    # Technology Filter
    st.subheader("📡 Technology Filter")
    tech_options = ["2G", "3G", "4G", "5G", "LTE", "GSM", "UMTS", "CDMA", "WiFi"]
    tech_sel = st.multiselect(
        "Select technologies",
        tech_options,
        default=[],
        help="Leave empty to include all technologies"
    )
    st.session_state.filters['tech_sel'] = tech_sel

# Main Content
st.markdown("Configure which datasets to include and apply global filters across all data sources.")

# Dataset Management Section
st.header("📋 Dataset Management")

enabled_sources = []
dataset_colors = {}

# Create columns for dataset cards
cols = st.columns(min(3, len(datasets)))
for i, (dataset_name, df) in enumerate(datasets.items()):
    with cols[i % 3]:
        with st.container():
            st.markdown(f"### 📊 {dataset_name}")
            
            # Enable/disable toggle
            enabled = st.checkbox(
                f"Enable {dataset_name}",
                value=dataset_name in st.session_state.filters.get('enabled_sources', []),
                key=f"enable_{dataset_name}"
            )
            
            if enabled:
                enabled_sources.append(dataset_name)
                
                # Color picker for this dataset
                default_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
                default_color = default_colors[i % len(default_colors)]
                
                color = st.color_picker(
                    f"Color for {dataset_name}",
                    value=st.session_state.filters['colors'].get(dataset_name, default_color),
                    key=f"color_{dataset_name}"
                )
                dataset_colors[dataset_name] = color
            
            # Dataset summary
            summary = get_dataset_summary(df)
            st.metric("Rows", f"{summary['total_rows']:,}")
            
            if summary['date_range']:
                start_date = summary['date_range'][0].strftime('%Y-%m-%d')
                end_date = summary['date_range'][1].strftime('%Y-%m-%d')
                st.markdown(f"**Date Range:** {start_date} to {end_date}")
            
            if summary['unique_callers'] > 0:
                st.markdown(f"**Unique Callers:** {summary['unique_callers']:,}")
            if summary['unique_callees'] > 0:
                st.markdown(f"**Unique Callees:** {summary['unique_callees']:,}")

# Update session state
st.session_state.filters['enabled_sources'] = enabled_sources
st.session_state.filters['colors'] = dataset_colors

# Mute Numbers Section
st.header("🔇 Mute Numbers")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📞 Top Numbers")
    
    if enabled_sources:
        # Get top numbers from enabled datasets
        enabled_dfs = [datasets[name] for name in enabled_sources]
        if enabled_dfs:
            combined_sample = pd.concat(enabled_dfs, ignore_index=True)
            top_numbers = get_top_numbers(combined_sample, top_n=20)
            
            if top_numbers['top_numbers']:
                st.markdown("**Most frequent numbers across all enabled datasets:**")
                
                # Create quick mute buttons
                mute_cols = st.columns(4)
                for i, number in enumerate(top_numbers['top_numbers'][:12]):  # Show top 12
                    with mute_cols[i % 4]:
                        if st.button(f"🔇 {number}", key=f"mute_{number}"):
                            if number not in st.session_state.filters['mute_numbers']:
                                st.session_state.filters['mute_numbers'].append(number)
                                st.rerun()
            else:
                st.info("No phone numbers found in enabled datasets")
    else:
        st.info("Enable datasets to see top numbers")

with col2:
    st.subheader("🚫 Custom Mute List")
    
    # Manual mute number input
    new_mute = st.text_input("Add number to mute", placeholder="1234567890")
    if st.button("Add to mute list") and new_mute:
        if new_mute not in st.session_state.filters['mute_numbers']:
            st.session_state.filters['mute_numbers'].append(new_mute)
            st.rerun()
    
    # Show current mute list
    if st.session_state.filters['mute_numbers']:
        st.markdown("**Currently muted:**")
        for i, number in enumerate(st.session_state.filters['mute_numbers']):
            col_num, col_btn = st.columns([3, 1])
            with col_num:
                st.markdown(f"• {number}")
            with col_btn:
                if st.button("❌", key=f"remove_mute_{i}"):
                    st.session_state.filters['mute_numbers'].remove(number)
                    st.rerun()
    else:
        st.info("No numbers muted")

# Apply Filters and Generate Combined Dataset
st.header("🔄 Apply Filters")

if st.button("🚀 Apply Filters and Generate Combined Dataset", type="primary"):
    with st.spinner("Applying filters and combining datasets..."):
        try:
            combined_df = apply_filters(
                datasets=datasets,
                enabled_sources=st.session_state.filters['enabled_sources'],
                mute_numbers=st.session_state.filters['mute_numbers'],
                time_range=st.session_state.filters['time_range'],
                min_duration=st.session_state.filters['min_duration'],
                tech_sel=st.session_state.filters['tech_sel']
            )
            
            # Store in session state
            st.session_state['active_df'] = combined_df
            
            if not combined_df.empty:
                st.success(f"✅ Combined dataset created with {len(combined_df):,} rows")
            else:
                st.warning("⚠️ No data remaining after applying filters")
                
        except Exception as e:
            st.error(f"❌ Error applying filters: {e}")

# Show Combined Dataset Summary
if 'active_df' in st.session_state and not st.session_state['active_df'].empty:
    st.header("📊 Combined Dataset Summary")
    
    combined_df = st.session_state['active_df']
    summary = get_dataset_summary(combined_df)
    
    # Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Rows", f"{summary['total_rows']:,}")
    with col2:
        if summary['unique_callers'] > 0:
            st.metric("Unique Callers", f"{summary['unique_callers']:,}")
    with col3:
        if summary['unique_callees'] > 0:
            st.metric("Unique Callees", f"{summary['unique_callees']:,}")
    with col4:
        if summary['total_duration'] > 0:
            st.metric("Total Duration", f"{summary['total_duration']:,.0f}s")
    with col5:
        if 'source' in combined_df.columns:
            st.metric("Data Sources", combined_df['source'].nunique())
    
    # Source distribution chart
    if 'source' in combined_df.columns:
        st.subheader("📈 Data Distribution by Source")
        source_counts = combined_df['source'].value_counts()
        
        # Use stored colors
        colors = [st.session_state.filters['colors'].get(source, '#1f77b4') 
                 for source in source_counts.index]
        
        fig = px.pie(
            values=source_counts.values,
            names=source_counts.index,
            title="Records by Data Source",
            color_discrete_sequence=colors
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Time series chart
    if 'ts' in combined_df.columns:
        st.subheader("📅 Activity Over Time")
        
        # Resample by day
        daily_counts = combined_df.set_index('ts').resample('D').size().reset_index()
        daily_counts.columns = ['Date', 'Count']
        
        if 'source' in combined_df.columns:
            # Group by source for colored time series
            source_daily = combined_df.set_index('ts').groupby('source').resample('D').size().reset_index()
            source_daily.columns = ['source', 'Date', 'Count']
            
            fig = px.line(
                source_daily, 
                x='Date', 
                y='Count', 
                color='source',
                title="Daily Activity by Source",
                color_discrete_map=st.session_state.filters['colors']
            )
        else:
            fig = px.line(
                daily_counts, 
                x='Date', 
                y='Count', 
                title="Daily Activity"
            )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Data preview
    st.subheader("🔍 Data Preview")
    column_config = get_cdr_column_config(combined_df)
    st.dataframe(combined_df.head(100), use_container_width=True, column_config=column_config, hide_index=True)
    
    # Download options
    st.subheader("💾 Download Combined Dataset")
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = combined_df.to_csv(index=False)
        st.download_button(
            "📥 Download as CSV",
            csv_data,
            "combined_cdr_data.csv",
            "text/csv",
            help="Download the filtered and combined dataset"
        )
    
    with col2:
        # Create summary report
        filter_summary = f"""
# CDR Data Filter Summary

## Applied Filters:
- **Enabled Sources**: {', '.join(st.session_state.filters['enabled_sources'])}
- **Muted Numbers**: {len(st.session_state.filters['mute_numbers'])} numbers
- **Time Range**: {st.session_state.filters['time_range'] if st.session_state.filters['time_range'] else 'All time'}
- **Min Duration**: {st.session_state.filters['min_duration']} seconds
- **Technologies**: {', '.join(st.session_state.filters['tech_sel']) if st.session_state.filters['tech_sel'] else 'All'}

## Results:
- **Total Records**: {summary['total_rows']:,}
- **Date Range**: {summary['date_range'][0].strftime('%Y-%m-%d') if summary['date_range'] else 'N/A'} to {summary['date_range'][1].strftime('%Y-%m-%d') if summary['date_range'] else 'N/A'}
- **Unique Callers**: {summary['unique_callers']:,}
- **Unique Callees**: {summary['unique_callees']:,}
"""
        
        st.download_button(
            "📄 Download Filter Report",
            filter_summary,
            "filter_report.md",
            "text/markdown",
            help="Download a summary of applied filters and results"
        )

else:
    st.info("👆 Apply filters to generate a combined dataset for analysis")

# Footer
st.markdown("---")
st.markdown("""
**💡 Tips:**
- **Enable Datasets**: Select which data sources to include in your analysis
- **Color Coding**: Assign colors to distinguish between data sources in visualizations
- **Mute Numbers**: Exclude specific phone numbers from analysis (useful for test numbers, system numbers, etc.)
- **Time Filters**: Focus on specific time periods across all datasets
- **Combined Dataset**: The filtered dataset will be available in other analysis pages
""")
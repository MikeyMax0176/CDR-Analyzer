import streamlit as st
import subprocess
import datetime
import io
import pandas as pd
from cdr_toolkit.storage import init_case_schema, init_schema_presets_table

# Page configuration
st.set_page_config(
    page_title="CDR Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schemas on app startup
if 'engine' not in st.session_state:
    st.session_state.engine = "cdr_toolkit.db"

# Initialize all schemas
init_schema_presets_table(st.session_state.engine)
init_case_schema(st.session_state.engine)

st.title("📊 CDR Analyzer")
st.markdown("Welcome to the CDR (Call Detail Record) Analysis Toolkit")

# Helper function for separator detection
def best_sep(sample: str):
    lines = sample.split('\n')[:5]
    comma_count = sum(line.count(',') for line in lines) / len(lines)
    tab_count = sum(line.count('\t') for line in lines) / len(lines)
    return '\t' if tab_count > comma_count else ','

# Main content area
st.markdown("""
## 🚀 Getting Started

This toolkit provides comprehensive CDR analysis capabilities:

### 📥 **Data Ingestion & Mapping**
- Upload CSV/TSV CDR files
- Map columns to standard schema
- Save and reuse mapping presets

### 🧪 **Quality Checks & Preview**
- Validate data quality
- Check for missing values and anomalies
- Preview data statistics

### 📊 **Statistics & Visualizations**
- Call volume analysis
- Temporal patterns
- Geographical distributions

### 🌐 **Network Analysis**
- Interactive network graphs
- Community detection
- Path finding
- Centrality analysis

### 🗺️ **Geospatial Analysis**
- Map visualizations
- Geofencing
- Location pins
- Movement patterns

### 🗂️ **Case Management**
- Organize investigations into cases
- Add notes and events
- Track timeline and evidence
- Coordinate team activities

---

## 📂 Sample Data Upload

Use the uploader below to get started with your CDR data:
""")

# File uploader
uploaded = st.file_uploader("Upload CDR (CSV/TSV/TXT)", type=["csv","tsv","txt"])
if uploaded:
    # Read sample to detect separator
    sample = uploaded.read(4096).decode("utf-8", errors="ignore")
    sep = best_sep(sample)
    uploaded.seek(0)
    
    try:
        df = pd.read_csv(uploaded, sep=sep, low_memory=False)
        st.success(f"✅ Loaded {len(df):,} rows (detected {'TAB' if sep=='\t' else 'COMMA'} separator)")
        
        # Show preview
        st.subheader("📋 Data Preview")
        st.dataframe(df.head(50), use_container_width=True)
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Rows", len(df))
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
        with col4:
            st.metric("Null Values", df.isnull().sum().sum())
        
        st.info("👈 Navigate to **'Ingest & Map Schema'** in the sidebar to configure column mapping and proceed with analysis.")
        
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        st.info("Please check your file format and try again. Supported formats: CSV, TSV, TXT")
else:
    st.info("👆 Upload a CDR file to begin analysis")

# Sidebar navigation guide
with st.sidebar:
    st.markdown("## 🧭 Navigation Guide")
    st.markdown("""
    1. **📥 Ingest & Map Schema** - Start here
    2. **🧪 Preview & Quality** - Check data quality  
    3. **📊 Stats & Visuals** - Explore patterns
    4. **🌐 Network Explorer** - Analyze connections
    5. **🗺️ Geofence & Pins** - Map locations
    6. **🗂️ Cases & Events** - Manage investigations
    """)

# Footer with system info
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 💾 Git Management")
    if st.button("📸 Save Git Snapshot"):
        try:
            ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
            commit_msg = f"snapshot: {ts}"
            add = subprocess.run(["git", "add", "-A"], capture_output=True, text=True, check=False)
            commit = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True, check=False)
            push = subprocess.run(["git", "push"], capture_output=True, text=True, check=False)
            if push.returncode == 0:
                st.success(f"✅ Snapshot saved! Commit: {commit_msg}")
            elif commit.returncode == 1 and 'nothing to commit' in commit.stderr:
                st.info("ℹ️ No changes to commit.")
            else:
                st.error(f"❌ Git push failed: {push.stderr}")
        except Exception as e:
            st.error(f"❌ Snapshot failed: {e}")

with col2:
    st.markdown("### ℹ️ System Info")
    st.markdown(f"**Database:** `{st.session_state.engine}`")
    st.markdown(f"**Session ID:** `{st.session_state.get('session_id', 'new')}`")
    
    # Database status
    try:
        from cdr_toolkit.storage import list_cases
        case_count = len(list_cases(st.session_state.engine))
        st.markdown(f"**Cases:** {case_count}")
    except:
        st.markdown("**Cases:** *Not accessible*")

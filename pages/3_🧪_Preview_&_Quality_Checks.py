import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.title("🧪 Preview & Quality Checks")
from cdr_toolkit.ui import render_snapshot_button

render_snapshot_button()

# --- Load active DataFrame ---
if "active_df" not in st.session_state or st.session_state["active_df"].empty:
    st.warning("No active dataset. Please select sources in the Datasets & Filters page.")
    st.page_link("pages/2_🗃️_Datasets_&_Filters.py", label="Go to Datasets & Filters", icon="🗃️")
    st.stop()

df = st.session_state["active_df"]

# --- Canonical fields ---
CANONICAL_FIELDS = [
    "call_id",
    "caller",
    "callee",
    "start_time",
    "duration",
    "imei",
    "imsi",
    "cell_id",
    "lac",
    "latitude",
    "longitude",
    "source",
]

# --- Column presence and type checks ---
col_stats = []
for col in CANONICAL_FIELDS:
    present = col in df.columns
    pct_present = df[col].notna().mean() * 100 if present else 0
    dtype = str(df[col].dtype) if present else "-"
    na_count = df[col].isna().sum() if present else "-"
    col_stats.append(
        {
            "Column": col,
            "Present (%)": f"{pct_present:.1f}%" if present else "0.0%",
            "Type": dtype,
            "NA Count": na_count,
        }
    )

# --- Duplicate call_id check ---
dup_callid = 0
if "call_id" in df.columns:
    dup_callid = df["call_id"].duplicated().sum()

# --- Outlier checks ---
outlier_rows = pd.DataFrame()
checks = []
if "duration" in df.columns:
    bad_duration = df[df["duration"] <= 0]
    checks.append(("Duration ≤ 0", len(bad_duration)))
    outlier_rows = pd.concat([outlier_rows, bad_duration])
if "start_time" in df.columns:
    try:
        times = pd.to_datetime(df["start_time"], errors="coerce")
        impossible_time = df[times > datetime.now()]
        checks.append(("Future timestamps", len(impossible_time)))
        outlier_rows = pd.concat([outlier_rows, impossible_time])
    except Exception:
        pass
if "caller" in df.columns and "callee" in df.columns:
    same_party = df[df["caller"] == df["callee"]]
    checks.append(("Caller == Callee", len(same_party)))
    outlier_rows = pd.concat([outlier_rows, same_party])

# --- Summary banner ---
st.info(
    f"**Rows:** {len(df):,} | **Columns:** {len(df.columns)} | **Duplicate call_id:** {dup_callid} | "
    + " | ".join([f"{desc}: {count}" for desc, count in checks])
)
st.page_link("pages/2_🗃️_Datasets_&_Filters.py", label="Back to Datasets & Filters", icon="🗃️")

# --- Column stats table ---
st.subheader("Column Presence & Type Checks")
st.dataframe(pd.DataFrame(col_stats))

# --- Outlier rows ---
st.subheader("Outlier Rows (duration ≤ 0, future timestamps, caller==callee)")
if not outlier_rows.empty:
    st.dataframe(outlier_rows.drop_duplicates(), use_container_width=True)
    csv = outlier_rows.drop_duplicates().to_csv(index=False)
    st.download_button("Download Outlier Rows as CSV", csv, "outliers.csv", "text/csv")
else:
    st.success("No outlier rows detected.")

# --- NA counts table ---
st.subheader("NA Counts by Column")
st.dataframe(df.isna().sum().reset_index().rename(columns={0: "NA Count", "index": "Column"}))

import streamlit as st
import pandas as pd
from cdr_toolkit.ingest import validate_cdr

st.header("Preview & Quality Checks")

uploaded = st.file_uploader("Upload CDR (CSV/TSV/TXT)", type=["csv","tsv","txt"])
if not uploaded:
    st.info("Upload a file to begin.")
    st.stop()

sample = uploaded.read(4096).decode("utf-8", errors="ignore")
sep = "\t" if sample.count("\t") > sample.count(",") else ","
uploaded.seek(0)
df = pd.read_csv(uploaded, sep=sep, low_memory=False)

st.success(f"Loaded {len(df):,} rows (detected {'TAB' if sep=='\\t' else 'COMMA'})")
st.dataframe(df.head(50), use_container_width=True)

result = validate_cdr(df)

if not result["errors"]:
    st.success("✅ No errors found!")
else:
    for err in result["errors"]:
        st.error(err)

for warn in result["warnings"]:
    st.warning(warn)

if result["nulls"]:
    st.subheader("Null Value Percentage per Column")
    st.table({k: f"{v:.1%}" for k, v in result["nulls"].items()})

st.subheader("Summary Statistics")
st.json(result["summary"])

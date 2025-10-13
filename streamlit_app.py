import io
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="CDR Analyzer", layout="wide")
st.title("CDR Analyzer")

def best_sep(sample:str)->str:
    return "\t" if sample.count("\t") > sample.count(",") else ","

uploaded = st.file_uploader("Upload CDR (CSV/TSV/TXT)", type=["csv","tsv","txt"])
if not uploaded:
    st.info("Upload a file to begin.")
    st.stop()

sample = uploaded.read(4096).decode("utf-8", errors="ignore")
sep = best_sep(sample)
uploaded.seek(0)
df = pd.read_csv(uploaded, sep=sep, low_memory=False)

st.success(f"Loaded {len(df):,} rows (detected {'TAB' if sep=='\\t' else 'COMMA'})")
st.dataframe(df.head(50), use_container_width=True)

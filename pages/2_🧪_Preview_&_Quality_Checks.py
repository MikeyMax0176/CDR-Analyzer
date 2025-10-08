import streamlit as st
import pandas as pd
from cdr_toolkit.ingest import validate_cdr

st.header("Preview & Quality Checks")

datasets = st.session_state.get("datasets", {})
if not datasets:
    st.info("No datasets loaded in session. Please ingest data first.")
    st.stop()

dataset_name = st.selectbox("Select dataset", list(datasets.keys()))
df = datasets[dataset_name]

st.dataframe(df.head(200), use_container_width=True)

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

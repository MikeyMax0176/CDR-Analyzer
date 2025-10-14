import streamlit as st
import pandas as pd
import base64
import networkx as nx
import io
import json

# Fixed color palette for communities (E)
PALETTE = [
    "#8dd3c7",
    "#ffffb3",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#d9d9d9",
    "#bc80bd",
    "#ccebc5",
    "#ffed6f",
    "#e41a1c",
    "#377eb8",
    "#4daf4a",
    "#984ea3",
    "#ff7f00",
    "#ffff33",
    "#a65628",
    "#f781bf",
    "#999999",
]


# Utility for robust ID conversion (C)
def _as_id(val, strip_non_digits=False):
    if pd.isna(val):
        return ""
    s = str(val)
    if s.lower() == "nan":
        return ""
    if strip_non_digits:
        s = "".join(c for c in s if c.isdigit())
    return s


# --- Robust Import Guard ---
try:
    from pyvis.network import Network
    import streamlit.components.v1 as components
    import community as community_louvain

    PYVIS_OK = True
except ModuleNotFoundError as e:
    PYVIS_OK = False
    st.error(
        f"""
    **PyVis Dependencies Missing**
    
    Install required packages:
    ```bash
    pip install pyvis python-louvain networkx
    ```
    
    Error: {e}
    """
    )
    st.stop()

st.title("🌐 Network Explorer")
from cdr_toolkit.ui import render_snapshot_button

render_snapshot_button()


import streamlit as st
import pandas as pd

import sys
import streamlit.components.v1 as components
from pyvis.network import Network


st.header("Interactive Call Network Explorer (PyVis)")

datasets = st.session_state.get("datasets", {})
if not datasets:
    st.info("No datasets loaded in session. Please ingest data first.")
    st.stop()

dataset_name = st.selectbox("Select dataset", list(datasets.keys()))
df = datasets[dataset_name]

st.markdown("""
Drag nodes to explore the call network. Node size = total calls. Edge thickness = call count.
Use the controls below to filter and focus the network.
""")


date_col = 'start_time' if 'start_time' in df else None
if date_col:
    ts = pd.to_datetime(df[date_col], errors="coerce", utc=True).dt.tz_convert(None)
    min_dt = pd.Timestamp(ts.min()).to_pydatetime()
    max_dt = pd.Timestamp(ts.max()).to_pydatetime()
    date_range = st.slider(
        "Date range",
        min_value=min_dt,
        max_value=max_dt,
        value=(min_dt, max_dt),
        format="YYYY-MM-DD"
    )
    start_dt, end_dt = [pd.Timestamp(d) for d in date_range]
    df = df[(ts >= start_dt) & (ts <= end_dt)]
min_weight = st.number_input("Minimum edge weight (calls)", min_value=1, value=1)
max_edges = st.number_input("Max edges to display", min_value=10, max_value=1000, value=200, step=10)
focus_number = st.text_input("Focus number (optional)")
ego_depth = st.selectbox("Ego depth (hops)", [1, 2], index=0)



# --- PyVis Network Explorer ---
if 'caller' in df and 'callee' in df:
    df['caller'] = df['caller'].astype(str)
    df['callee'] = df['callee'].astype(str)
    edge_counts = df.groupby(['caller', 'callee']).size().reset_index(name='count')
    edge_counts = edge_counts[edge_counts['count'] >= min_weight]
    # Ego/focus filter
    focus_set = set()
    if focus_number:
        focus_number = str(focus_number)
        focus_set.add(focus_number)
        if ego_depth == 1:
            neighbors = set(edge_counts.loc[(edge_counts['caller'] == focus_number), 'callee'])
            neighbors |= set(edge_counts.loc[(edge_counts['callee'] == focus_number), 'caller'])
            focus_set |= neighbors
            edge_counts = edge_counts[(edge_counts['caller'].isin(focus_set)) & (edge_counts['callee'].isin(focus_set))]
        elif ego_depth == 2:
            neighbors1 = set(edge_counts.loc[(edge_counts['caller'] == focus_number), 'callee'])
            neighbors1 |= set(edge_counts.loc[(edge_counts['callee'] == focus_number), 'caller'])
            neighbors2 = set(edge_counts.loc[(edge_counts['caller'].isin(neighbors1)), 'callee'])
            neighbors2 |= set(edge_counts.loc[(edge_counts['callee'].isin(neighbors1)), 'caller'])
            focus_set |= neighbors1 | neighbors2
            edge_counts = edge_counts[(edge_counts['caller'].isin(focus_set)) & (edge_counts['callee'].isin(focus_set))]
    # Limit max edges
    edge_counts = edge_counts.sort_values('count', ascending=False).head(max_edges)
    # Node weights: in+out degree (after edge filter)
    all_nodes = pd.concat([edge_counts['caller'], edge_counts['callee']])
    node_weights = all_nodes.value_counts().to_dict()
    def _scale(val, vmin, vmax, omin, omax):
        if vmax == vmin:
            return (omin + omax) // 2
        return int(omin + (val-vmin)*(omax-omin)/(vmax-vmin))
    min_size, max_size = 12, 60
    min_wt, max_wt = min(node_weights.values(), default=1), max(node_weights.values(), default=1)
    min_count, max_count = edge_counts['count'].min() if not edge_counts.empty else 1, edge_counts['count'].max() if not edge_counts.empty else 1
    # Build PyVis network
    net = Network(height="700px", width="100%", directed=True)
    net.set_options('{ "physics": { "enabled": true, "barnesHut": { "gravitationalConstant": -8000, "springLength": 250 } }, "edges": { "smooth": true } }')
    # Add nodes
    for n, wt in node_weights.items():
        node_class = "target" if focus_number and n == focus_number else ("neighbor" if focus_number and n in focus_set and n != focus_number else "")
        color = "#d32f2f" if node_class=="target" else ("#fbc02d" if node_class=="neighbor" else "#1976d2")
        net.add_node(n, label=n, size=_scale(wt, min_wt, max_wt, min_size, max_size), color=color)
    # Add edges
    for _, row in edge_counts.iterrows():
        width = _scale(row['count'], min_count, max_count, 1, 10)
        net.add_edge(str(row['caller']), str(row['callee']), value=width, title=str(row['count']), color="#90caf9")
    # Save and embed
    net.save_graph("network.html")
    with open("network.html", "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=720, scrolling=True)
    # Download buttons
    nodes_df = pd.DataFrame({ 'id': list(node_weights.keys()), 'weight': list(node_weights.values()) })
    edges_df = edge_counts.rename(columns={'caller': 'source', 'callee': 'target', 'count': 'weight'})
    st.download_button("Download nodes.csv", nodes_df.to_csv(index=False), "nodes.csv")
    st.download_button("Download edges.csv", edges_df.to_csv(index=False), "edges.csv")
else:
    st.info("No 'caller' or 'callee' columns found in this dataset.")

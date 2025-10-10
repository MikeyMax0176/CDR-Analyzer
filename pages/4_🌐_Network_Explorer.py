
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from pyvis.network import Network
import base64

# Set wide layout
st.set_page_config(layout="wide")

st.header("Interactive Call Network Explorer (PyVis)")

datasets = st.session_state.get("datasets", {})
if not datasets:
    st.info("No datasets loaded in session. Please ingest data first.")
    st.stop()

dataset_name = st.selectbox("Select dataset", list(datasets.keys()))
df = datasets[dataset_name]

# Sidebar - Network Controls
with st.sidebar:
    st.header("Network Controls")
    physics_on = st.toggle("Physics Enabled", value=False)
    solver = st.selectbox("Physics Solver", 
                         ["barnesHut", "repulsion", "forceAtlas2Based"], 
                         index=0)
    gravity = st.slider("Gravity", min_value=-100, max_value=0, value=-30, step=5)
    spring_length = st.slider("Spring Length", min_value=50, max_value=500, value=200, step=25)
    show_toolbar = st.toggle("Show Toolbar", value=False)
    show_labels = st.toggle("Show Labels", value=True)

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
    # Build PyVis network with vis.js options
    net = Network(height="90vh", width="100%", directed=True)
    
    # Force nodes to stay where dropped - disable physics and stabilization
    options = {
        "physics": {
            "enabled": False
        },
        "stabilization": {
            "iterations": 0
        },
        "interaction": {
            "dragNodes": True
        },
        "edges": {"smooth": True},
        "nodes": {"chosen": True}
    }
    if not show_labels:
        options["nodes"]["font"] = {"size": 0}
    
    # Set options
    import json
    net.set_options(json.dumps(options))
    
    # Show toolbar if requested
    if show_toolbar:
        net.show_buttons(['physics','interaction','layout','nodes','edges'])
    # Add nodes - all with physics=False to prevent movement
    for n, wt in node_weights.items():
        node_class = "target" if focus_number and n == focus_number else ("neighbor" if focus_number and n in focus_set and n != focus_number else "")
        color = "#d32f2f" if node_class=="target" else ("#fbc02d" if node_class=="neighbor" else "#1976d2")
        label = n if show_labels else ""
        net.add_node(n, label=label, size=_scale(wt, min_wt, max_wt, min_size, max_size), 
                    color=color, physics=False)
    # Add edges
    for _, row in edge_counts.iterrows():
        width = _scale(row['count'], min_count, max_count, 1, 10)
        net.add_edge(str(row['caller']), str(row['callee']), value=width, title=str(row['count']), color="#90caf9")
    # Save and embed
    graph_filename = "cdr_network.html"
    net.save_graph(graph_filename)
    
    with open(graph_filename, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Embed the network
    components.html(html_content, height=int(0.9 * 600), scrolling=True)
    
    # Download buttons and links
    nodes_df = pd.DataFrame({ 'id': list(node_weights.keys()), 'weight': list(node_weights.values()) })
    edges_df = edge_counts.rename(columns={'caller': 'source', 'callee': 'target', 'count': 'weight'})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.download_button("Download nodes.csv", nodes_df.to_csv(index=False), "nodes.csv")
    with col2:
        st.download_button("Download edges.csv", edges_df.to_csv(index=False), "edges.csv")
    with col3:
        st.download_button("Download Network HTML", html_content, graph_filename, 
                          mime="text/html")
    with col4:
        # Create data URL for full-screen viewing
        encoded_html = base64.b64encode(html_content.encode()).decode()
        data_url = f"data:text/html;base64,{encoded_html}"
        st.markdown(f'<a href="{data_url}" target="_blank">🔗 Open full-screen</a>', 
                   unsafe_allow_html=True)
    with col5:
        # Add page link to full-screen view (Ctrl/Cmd-click for new tab)
        st.page_link("pages/5_🖥️_Network_Fullscreen.py", label="🖥️ Full-screen View")
else:
    st.info("No 'caller' or 'callee' columns found in this dataset.")

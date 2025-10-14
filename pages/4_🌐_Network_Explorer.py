import streamlit as st
import pandas as pd
import networkx as nx
import base64
import json
from datetime import datetime, timedelta

# Robust dependency guard for pyvis
PYVIS_OK = True
try:
    from pyvis.network import Network
    import streamlit.components.v1 as components
except Exception as e:
    st.error(f"PyVis is required for network visualization. Install with: pip install pyvis\nError: {e}")
    PYVIS_OK = False

# Robust dependency guard for Louvain
LOUVAIN_OK = True
try:
    import community as community_louvain
except Exception as e:
    LOUVAIN_OK = False
    st.warning("Louvain community detection not available. Install with: pip install python-louvain\n\nError: " + str(e))

# Before rendering the graph, check PyVis
if not PYVIS_OK:
    st.stop()

st.title("🌐 Network Explorer")

# Tool ribbon - custom controls
with st.container():
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        physics = st.checkbox("Physics", value=True)
    with col2:
        freeze = st.checkbox("Freeze positions", value=False)
    with col3:
        labels = st.checkbox("Labels", value=True)
    with col4:
        show_toolbar = st.checkbox("Show toolbar", value=False)
    
    # Second row
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        focus_number = st.text_input("Focus number", placeholder="1234567890")
    with col6:
        ego_depth = st.selectbox("Ego depth", [1, 2], index=0)
    with col7:
        edge_min_weight = st.number_input("Edge min weight", min_value=1, value=1)
    with col8:
        max_edges = st.number_input("Max edges", min_value=10, value=1000)
    
    # Third row - conditional controls
    if LOUVAIN_OK:
        color_by_cluster = st.checkbox("Color by cluster", value=False, help="Use Louvain community detection to color nodes by cluster")
    else:
        color_by_cluster = False

# Get the active dataset
df = None
if 'active_df' in st.session_state and not st.session_state['active_df'].empty:
    df = st.session_state['active_df'].copy()
elif 'datasets' in st.session_state and st.session_state.datasets:
    # Use first available dataset if no active one
    dataset_name = list(st.session_state.datasets.keys())[0]
    df = st.session_state.datasets[dataset_name].copy()

if df is None or df.empty:
    st.warning("⚠️ No data available. Please load and filter data in the 'Datasets & Filters' page first.")
    st.stop()

# Date range filter if start_time exists
if 'start_time' in df.columns:
    st.subheader("📅 Time Filter")
    try:
        df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
        df = df.dropna(subset=['start_time'])
        
        if not df.empty:
            min_date = df['start_time'].min().date()
            max_date = df['start_time'].max().date()
            
            date_range = st.slider(
                "Select date range",
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date),
                format="YYYY-MM-DD"
            )
            
            # Filter by date range
            start_dt = pd.Timestamp(date_range[0])
            end_dt = pd.Timestamp(date_range[1]) + timedelta(days=1)
            df = df[(df['start_time'] >= start_dt) & (df['start_time'] < end_dt)]
    except Exception as e:
        st.info(f"Date filtering not available: {e}")

# Build edge table from caller-callee pairs
if 'caller' not in df.columns or 'callee' not in df.columns:
    st.error("Dataset must have 'caller' and 'callee' columns for network analysis.")
    st.stop()

# Group by caller-callee pairs and count
edge_df = df.groupby(['caller', 'callee']).size().reset_index(name='weight')
edge_df = edge_df[edge_df['weight'] >= edge_min_weight]
edge_df = edge_df.sort_values('weight', ascending=False).head(max_edges)

if edge_df.empty:
    st.warning("No edges found with the current filters.")
    st.stop()

# Focus on ego network if specified
if focus_number.strip():
    focus = focus_number.strip()
    
    # Get ego network
    if ego_depth == 1:
        # Direct connections only
        ego_edges = edge_df[
            (edge_df['caller'] == focus) | 
            (edge_df['callee'] == focus)
        ]
    else:  # ego_depth == 2
        # Two-hop network
        direct_neighbors = set()
        direct_edges = edge_df[
            (edge_df['caller'] == focus) | 
            (edge_df['callee'] == focus)
        ]
        for _, row in direct_edges.iterrows():
            direct_neighbors.add(row['caller'])
            direct_neighbors.add(row['callee'])
        
        # Find edges involving direct neighbors
        ego_edges = edge_df[
            edge_df['caller'].isin(direct_neighbors) | 
            edge_df['callee'].isin(direct_neighbors)
        ]
    
    edge_df = ego_edges

if edge_df.empty:
    st.warning(f"No connections found for {focus_number}")
    st.stop()

# Create NetworkX graph for analysis
G = nx.from_pandas_edgelist(edge_df, source='caller', target='callee', 
                           edge_attr='weight', create_using=nx.DiGraph())

# Louvain community detection (optional coloring)
node_colors = {}
if LOUVAIN_OK and color_by_cluster and G.number_of_nodes() > 1:
    try:
        # Convert to undirected for community detection
        G_undirected = G.to_undirected()
        partition = community_louvain.best_partition(G_undirected)
        
        # Assign colors based on community
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        for node, community_id in partition.items():
            node_colors[node] = colors[community_id % len(colors)]
    except Exception as e:
        st.info(f"Community detection not available: {e}")

# Create PyVis network
net = Network(height="78vh", width="100%", directed=True)

# Set PyVis options for interactivity
options = {
    "physics": {
        "enabled": bool(physics and not freeze),
        "stabilization": {"enabled": True, "iterations": 150}
    },
    "interaction": {
        "dragNodes": not freeze,
        "hover": True
    },
    "edges": {"smooth": True},
    "nodes": {"chosen": True}
}

if not labels:
    options["nodes"] = {"font": {"size": 0}}

net.set_options(json.dumps(options))

if show_toolbar:
    net.show_buttons(["physics", "interaction", "layout", "nodes", "edges"])

# Add nodes with community colors if available
for node in G.nodes():
    color = node_colors.get(node, '#1f77b4')
    label = str(node) if labels else ""
    
    # Node positioning
    node_options = {"physics": not freeze}
    if freeze:
        node_options["fixed"] = {'x': True, 'y': True}
    else:
        node_options["fixed"] = False
    
    net.add_node(node, label=label, color=color, **node_options)

# Add edges
for _, row in edge_df.iterrows():
    net.add_edge(row['caller'], row['callee'], 
                width=min(row['weight'] / 2, 10),  # Scale edge width
                label=str(row['weight']))

# Save and display network
graph_filename = "cdr_network.html"
try:
    net.save_graph(graph_filename)
except AttributeError:
    try:
        net.save(graph_filename)
    except AttributeError:
        # Alternative method for older PyVis versions
        net.write_html(graph_filename)

# Read the HTML file and display
with open(graph_filename, "r", encoding="utf-8") as f:
    html_content = f.read()

components.html(html_content, height=600, scrolling=True)

# Build data URL and expose NEW-TAB openers
encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
data_url = f"data:text/html;base64,{encoded}"
st.link_button("🖥️ Open Network (Fullscreen)", data_url, help="Opens in a new browser tab")
st.markdown(f'<a href="{data_url}" target="_blank" rel="noopener noreferrer">🔗 Open full-screen in new tab</a>', unsafe_allow_html=True)

# Save html_content to session for Network Fullscreen launcher page
st.session_state["last_net_html"] = html_content

# Download options
col1, col2 = st.columns(2)
with col1:
    nodes_df = pd.DataFrame(list(G.nodes()), columns=['node'])
    nodes_csv = nodes_df.to_csv(index=False)
    st.download_button("📥 Download nodes.csv", nodes_csv, "nodes.csv", "text/csv")

with col2:
    edges_csv = edge_df.to_csv(index=False)
    st.download_button("📥 Download edges.csv", edges_csv, "edges.csv", "text/csv")

# Data Viz Toolbox
st.subheader("📊 Data Viz Toolbox")

viz_option = st.selectbox(
    "Choose visualization:",
    ["Top Pairs", "Top Callers", "Degree Distribution", "Time Series"]
)

if viz_option == "Top Pairs":
    st.write("**Top 20 Caller-Callee Pairs**")
    top_pairs = edge_df.head(20).copy()
    top_pairs['pair'] = top_pairs['caller'] + ' → ' + top_pairs['callee']
    st.dataframe(top_pairs[['pair', 'weight']])
    st.bar_chart(top_pairs.set_index('pair')['weight'])

elif viz_option == "Top Callers":
    st.write("**Top 20 Callers by Total Calls**")
    caller_stats = edge_df.groupby('caller')['weight'].sum().sort_values(ascending=False).head(20)
    st.bar_chart(caller_stats)

elif viz_option == "Degree Distribution":
    st.write("**Network Degree Distribution**")
    degrees = dict(G.degree())
    degree_counts = pd.Series(degrees).value_counts().sort_index()
    st.bar_chart(degree_counts)

elif viz_option == "Time Series":
    if 'start_time' in df.columns:
        st.write("**Daily Call Volume**")
        try:
            daily_calls = df.set_index('start_time').resample('D').size()
            st.line_chart(daily_calls)
        except Exception as e:
            st.info(f"Time series not available: {e}")
    else:
        st.info("Time series requires 'start_time' column in the dataset.")

# Network stats
st.subheader("📈 Network Statistics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Nodes", len(G.nodes()))
with col2:
    st.metric("Edges", len(G.edges()))
with col3:
    if len(G.nodes()) > 0:
        avg_degree = sum(dict(G.degree()).values()) / len(G.nodes())
        st.metric("Avg Degree", f"{avg_degree:.1f}")
with col4:
    if LOUVAIN_OK and 'partition' in locals():
        num_communities = len(set(partition.values()))
        st.metric("Communities", num_communities)
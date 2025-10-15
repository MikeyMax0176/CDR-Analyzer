import numpy as np
import random

import streamlit as st
import pandas as pd
import networkx as nx
import json
import base64
from datetime import datetime, timedelta
import itertools


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

if not PYVIS_OK:
    st.stop()


st.title("🌐 Network Explorer")

# --- TOOL RIBBON ---
with st.container():
    col1, col2, col3, col4, col5 = st.columns([2,2,2,2,2])
    with col1:
        physics_preset = st.radio("Physics preset", ["Stable (freeze)", "Exploration"], index=0)
    with col2:
        lock_all = st.checkbox("Lock all", value=False)
        unlock_all = st.checkbox("Unlock all", value=False)
    with col3:
        show_labels = st.toggle("Show labels", value=True)
        show_toolbar = st.checkbox("Toolbar", value=False)
    with col4:
        focus_number = st.text_input("Focus number", placeholder="1234567890")
        ego_depth = st.selectbox("Ego depth", [1, 2], index=0)
    with col5:
        min_weight = st.number_input("Edge min weight", min_value=1, value=1)
        max_edges = st.number_input("Max edges", min_value=10, value=500)
    # Advanced physics controls
    colA, colB = st.columns([1,1])
    with colA:
        freeze_after_stabilize = st.toggle("Freeze after stabilize", value=True, help="When enabled, uses a precomputed layout and disables live physics.")
    with colB:
        jitter_clicked = st.button("Jitter 5%", help="Randomly jitter current positions by ±5% (non-exploration presets)")
    # Louvain toggle
    if LOUVAIN_OK:
        color_by_cluster = st.checkbox("Color by cluster", value=False, help="Use Louvain community detection to color nodes by cluster")
    else:
        color_by_cluster = False




# --- SIDEBAR FILTERS ---
with st.sidebar:
    st.header("Filters")

df = None
if 'active_df' in st.session_state and not st.session_state['active_df'].empty:
    df = st.session_state['active_df'].copy()
elif 'datasets' in st.session_state and st.session_state.datasets:
    dataset_name = list(st.session_state.datasets.keys())[0]
    df = st.session_state.datasets[dataset_name].copy()

if df is None or df.empty:
    st.warning("⚠️ No data available. Please load and filter data in the 'Datasets & Filters' page first.")
    st.stop()

# Source filter
if 'source' in df.columns:
    all_sources = sorted(df['source'].dropna().unique())
    selected_sources = st.multiselect("Data sources", all_sources, default=all_sources)
    color_by_source = st.checkbox("Color by source", value=False)
    df = df[df['source'].isin(selected_sources)]
else:
    color_by_source = False

# Call type filter (only if manageable unique values)
if 'call_type' in df.columns:
    all_types = sorted(df['call_type'].dropna().unique())
    if len(all_types) <= 20:
        selected_types = st.multiselect("Call types", all_types, default=all_types)
        df = df[df['call_type'].isin(selected_types)]

# Direction filter (only if manageable unique values)
if 'direction' in df.columns:
    all_dirs = sorted(df['direction'].dropna().unique())
    if len(all_dirs) <= 20:
        selected_dirs = st.multiselect("Directions", all_dirs, default=all_dirs)
        df = df[df['direction'].isin(selected_dirs)]

# Date range filter with robust timezone/empty handling
if 'start_time' in df.columns:
    ts_utc = pd.to_datetime(df['start_time'], errors="coerce", utc=True)
    ts = ts_utc.dt.tz_convert(None)
    valid = ts.dropna()
    if not valid.empty:
        min_dt = valid.min().to_pydatetime()
        max_dt = valid.max().to_pydatetime()
        if min_dt == max_dt:
            max_dt = min_dt + pd.Timedelta(days=1)
        start_dt, end_dt = st.slider(
            "Date range",
            min_value=min_dt,
            max_value=max_dt,
            value=(min_dt, max_dt),
            format="YYYY-MM-DD",
        )
        mask = (ts >= pd.Timestamp(start_dt)) & (ts <= pd.Timestamp(end_dt))
        df = df.loc[mask]
    else:
        st.info("No valid timestamps to filter.")

# --- BUILD EDGES ---
# Only keep rows matching all filters above
if 'caller' not in df.columns or 'callee' not in df.columns:
    st.error("Dataset must have 'caller' and 'callee' columns for network analysis.")
    st.stop()

edge_df = df.groupby(['caller', 'callee']).size().reset_index(name='count')
edge_df = edge_df[edge_df['caller'] != edge_df['callee']]  # Drop self-loops
edge_df = edge_df[edge_df['count'] >= min_weight]
edge_df = edge_df.sort_values('count', ascending=False).head(max_edges)

# Ego filter
if focus_number.strip():
    focus = focus_number.strip()
    if ego_depth == 1:
        ego_edges = edge_df[(edge_df['caller'] == focus) | (edge_df['callee'] == focus)]
    else:
        # 2-hop ego network
        direct = set(edge_df[(edge_df['caller'] == focus) | (edge_df['callee'] == focus)]['caller'].tolist() + edge_df[(edge_df['caller'] == focus) | (edge_df['callee'] == focus)]['callee'].tolist())
        ego_edges = edge_df[edge_df['caller'].isin(direct) | edge_df['callee'].isin(direct)]
    edge_df = ego_edges

if edge_df.empty:
    st.warning("No edges found with the current filters.")
    st.stop()

# Node weights
node_weights = edge_df['caller'].value_counts() + edge_df['callee'].value_counts()
node_weights = node_weights.fillna(0)

def build_layout(G: nx.Graph, preset: str, focus_number: str | None) -> tuple[dict | None, dict | None]:
    """Return (positions, vis_layout) for the given preset. Mutually exclusive behavior."""
    if preset == "Exploration":
        return None, None
    elif preset == "Stable (freeze)":
        pos = nx.spring_layout(G, seed=42, iterations=250)
        # Scale to pixels
        scaled_pos = {}
        for n, (x, y) in pos.items():
            scaled_pos[n] = (int(x * 800), int(y * 800))
        return scaled_pos, None
    else:
        return None, None

# --- BUILD GRAPH ---
G = nx.from_pandas_edgelist(edge_df, source='caller', target='callee', edge_attr='count', create_using=nx.DiGraph())
G_undirected = G.to_undirected()

# --- COMMUNITY DETECTION ---
partition = None
node_colors = {}
if LOUVAIN_OK and color_by_cluster and G.number_of_nodes() > 1:
    try:
        partition = community_louvain.best_partition(G_undirected)
        palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
        for node, comm in partition.items():
            node_colors[node] = palette[comm % len(palette)]
    except Exception as e:
        st.info(f"Community detection not available: {e}")

# --- COLOR BY SOURCE ---
source_colors = {}
if color_by_source and 'source' in df.columns:
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    sources = sorted(df['source'].dropna().unique())
    for i, s in enumerate(sources):
        source_colors[s] = palette[i % len(palette)]
    st.session_state['source_colors'] = source_colors
else:
    source_colors = st.session_state.get('source_colors', {})

# --- POSITIONS AND PHYSICS ---
focus_clean = (focus_number.strip() or None)
positions, vis_layout = build_layout(G_undirected, physics_preset, focus_clean)

# Apply jitter if requested (only when we have positions)
if "_pos_cache" not in st.session_state:
    st.session_state["_pos_cache"] = None
if positions:
    st.session_state["_pos_cache"] = positions.copy()
if jitter_clicked and st.session_state.get("_pos_cache"):
    base = st.session_state["_pos_cache"]
    jittered = {}
    for n, (x, y) in base.items():
        fx = 1.0 + random.uniform(-0.05, 0.05)
        fy = 1.0 + random.uniform(-0.05, 0.05)
        jittered[n] = (int(x * fx), int(y * fy))
    positions = jittered
    st.session_state["_pos_cache"] = jittered.copy()


# --- PYVIS NETWORK ---
from pyvis.network import Network
net = Network(height="78vh", width="100%", directed=True)

# Build options without conflicts
opts = {
    "interaction": {"dragNodes": True, "hover": True},
    "nodes": {"chosen": True},
    "edges": {"smooth": True}
}

# Physics
live_physics = physics_preset == "Exploration" and not freeze_after_stabilize
if live_physics:
    opts["physics"] = {
        "enabled": True,
        "solver": "barnesHut",
        "barnesHut": {
            "gravitationalConstant": -2000,
            "centralGravity": 0.05,
            "springLength": 80,
            "springConstant": 0.03,
            "avoidOverlap": 0.3
        },
        "timestep": 0.4,
        "damping": 0.85,
        "maxVelocity": 20,
        "minVelocity": 1,
        "stabilization": {"enabled": True, "iterations": 200}
    }
else:
    opts["physics"] = {"enabled": False}

# Labels
if not show_labels:
    opts["nodes"]["font"] = {"size": 0}

# No hierarchical layout in this version


# Always pass JSON string to set_options
net.set_options(json.dumps(opts))

# Toolbar with error protection
try:
    if show_toolbar:
        net.show_buttons(filter_=['physics','interaction','layout','nodes','edges'])
except Exception as e:
    st.warning(f"Toolbar unavailable: {e}")

    # --- ADD NODES ---
for node in G.nodes():
    # Node size by degree
    degree = node_weights.get(node, 1)
    size = min(max(12, degree * 2), 60)
    
    # Node color
    color = '#1f77b4'
    if color_by_source and 'source' in df.columns:
        # Use first source for this node
        sources = df[(df['caller'] == node) | (df['callee'] == node)]['source'].unique()
        if len(sources) > 0:
            color = source_colors.get(sources[0], '#1f77b4')
    elif color_by_cluster and node in node_colors:
        color = node_colors[node]
    
    # Node label
    label = str(node) if show_labels else ""
    
    # Base properties
    base_props = {
        "label": label,
        "size": size,
        "color": color,
        "physics": live_physics,
        "fixed": False
    }
    
    # Node images (feature removed)
    
    # Tooltip with call stats
    first_ts = "Unknown"
    last_ts = "Unknown"
    if 'start_time' in df.columns:
        node_calls = df[(df['caller'] == node) | (df['callee'] == node)]
        if not node_calls.empty:
            try:
                timestamps = pd.to_datetime(node_calls['start_time'], errors='coerce').dropna()
                if not timestamps.empty:
                    first_ts = timestamps.min().strftime('%Y-%m-%d %H:%M')
                    last_ts = timestamps.max().strftime('%Y-%m-%d %H:%M')
            except Exception:
                pass
    
    base_props["title"] = f"Total calls: {degree}\\nFirst seen: {first_ts}\\nLast seen: {last_ts}"
    
    # Position handling
    if positions is not None:  # Non-hierarchical presets or frozen exploration
        xy = positions.get(node, (0, 0))
        base_props["x"] = xy[0]
        base_props["y"] = xy[1]
        base_props["physics"] = False  # Force physics off to prevent re-layout
    
    # Lock/Unlock overrides
    if lock_all:
        base_props["fixed"] = {"x": True, "y": True}
        base_props["physics"] = False
    elif unlock_all:
        base_props["fixed"] = False
    
    net.add_node(node, **base_props)

    # --- ADD EDGES ---
for _, row in edge_df.iterrows():
    src, tgt, weight = row['caller'], row['callee'], row['count']
    edge_opts = {"width": min(weight / 2, 10), "label": str(weight)}
    # Edge color
    if focus_number.strip():
        if src == focus_number.strip():
            edge_opts["color"] = "#2ca02c"  # outbound green
        elif tgt == focus_number.strip():
            edge_opts["color"] = "#d62728"  # inbound red
        else:
            edge_opts["color"] = "#1f77b4"
    else:
        edge_opts["color"] = "#1f77b4"
    net.add_edge(src, tgt, **edge_opts)


# --- SAVE + EMBED + FULLSCREEN ---
graph_filename = "cdr_network.html"
try:
    net.save_graph(graph_filename)
except AttributeError:
    try:
        net.save(graph_filename)
    except AttributeError:
        net.write_html(graph_filename)
with open(graph_filename, "r", encoding="utf-8") as f:
    html_content = f.read()
components.html(html_content, height=600, scrolling=True)
encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
data_url = f"data:text/html;base64,{encoded}"
st.link_button("🖥️ Open Network (Fullscreen)", data_url, help="Opens in a new browser tab")
st.session_state["last_net_html"] = html_content

# --- QUICK STATS ---
st.subheader("📈 Network Statistics")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Nodes", len(G.nodes()))
with col2:
    st.metric("Edges", len(G.edges()))
with col3:
    st.metric("Total Calls", int(edge_df['count'].sum()))
with col4:
    if LOUVAIN_OK and partition:
        st.metric("Communities", len(set(partition.values())))

"""
Below this point previously existed a duplicated, older implementation of the page
that conflicted with the new filters and graph builder. It has been removed to
avoid double-rendering and widget conflicts.
"""
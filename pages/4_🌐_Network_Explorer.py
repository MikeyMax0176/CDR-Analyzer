
import streamlit as st
import pandas as pd
import base64
import networkx as nx
import io
import json

# Set wide layout
st.set_page_config(layout="wide")

# --- Robust Import Guard ---
try:
    from pyvis.network import Network
    import streamlit.components.v1 as components
    import community as community_louvain
    PYVIS_OK = True
except ModuleNotFoundError as e:
    PYVIS_OK = False
    st.error(f"""
    **PyVis Dependencies Missing**
    
    Install required packages:
    ```bash
    pip install pyvis python-louvain networkx
    ```
    
    Error: {e}
    """)
    st.stop()

st.title("🌐 Network Explorer")

# Prefer active_df if available, otherwise use dataset selection
if 'active_df' in st.session_state and not st.session_state['active_df'].empty:
    df = st.session_state['active_df']
    st.success(f"📊 Using combined filtered dataset ({len(df):,} rows from {df['source'].nunique() if 'source' in df.columns else 1} source(s))")
    
    # Show source distribution if multiple sources
    if 'source' in df.columns and df['source'].nunique() > 1:
        source_counts = df['source'].value_counts()
        st.markdown("**Data Sources:**")
        cols = st.columns(min(4, len(source_counts)))
        for i, (source, count) in enumerate(source_counts.items()):
            with cols[i % 4]:
                color = st.session_state.get('filters', {}).get('colors', {}).get(source, '#1f77b4')
                st.markdown(f"<span style='color: {color}'>●</span> {source}: {count:,}", unsafe_allow_html=True)
else:
    datasets = st.session_state.get("datasets", {})
    if not datasets:
        st.info("No datasets loaded in session. Please ingest data first.")
        st.stop()

    dataset_name = st.selectbox("Select dataset", list(datasets.keys()))
    df = datasets[dataset_name]
    st.info("💡 Tip: Use 'Datasets & Filters' page to create a combined filtered dataset for enhanced analysis.")

st.header("Interactive Call Network Explorer (PyVis)")

# Sidebar - Network Controls
with st.sidebar:
    st.header("🎛️ Network Controls")
    
    # Community Detection
    st.subheader("🔍 Community Detection")
    color_by_cluster = st.toggle("Color by cluster", value=False)
    
    # Node Images (Dossier)
    st.subheader("🖼️ Node Images")
    uploaded_images = st.file_uploader(
        "Upload node images (filename = phone number)",
        type=["png", "jpg", "jpeg", "gif"],
        accept_multiple_files=True,
        help="Upload images with filenames matching phone numbers (e.g., '1234567890.jpg')"
    )
    
    # Edge Styling
    st.subheader("🔗 Edge Styling")
    edge_color_mode = st.selectbox(
        "Edge colors",
        ["by weight", "single color", "inbound vs outbound (focus)"],
        index=0
    )
    
    # Search/Highlight
    st.subheader("🔍 Search & Highlight")
    search_query = st.text_input("Search nodes (contains)", placeholder="Enter phone number...")
    
    # Physics Controls
    st.subheader("⚛️ Physics")
    enable_physics_temp = st.toggle("Enable physics temporarily", value=False)
    freeze_positions = st.toggle("Freeze positions", value=True)
    
    # Color Pickers
    st.subheader("🎨 Node Colors")
    primary_color = st.color_picker("Primary nodes", "#1976d2")
    neighbor_color = st.color_picker("Neighbor nodes", "#fbc02d") 
    target_color = st.color_picker("Target nodes", "#d32f2f")
    show_legend = st.toggle("Show legend", value=True)
    
    # Path Finder
    st.subheader("🛤️ Path Finder")
    path_from = st.text_input("From node", placeholder="Source phone number")
    path_to = st.text_input("To node", placeholder="Target phone number")
    show_path_only = st.toggle("Show path subgraph only", value=False)
    
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
    
    # Path finding logic
    path_nodes = set()
    if path_from and path_to:
        try:
            # Build networkx graph for path finding
            G_path = nx.from_pandas_edgelist(edge_counts, 'caller', 'callee', 'count')
            if path_from in G_path.nodes() and path_to in G_path.nodes():
                shortest_path = nx.shortest_path(G_path, path_from, path_to)
                path_nodes = set(shortest_path)
                st.success(f"📍 Shortest path: {' → '.join(shortest_path)} ({len(shortest_path)-1} hops)")
                
                if show_path_only:
                    # Filter edges to only show path
                    path_edges = [(shortest_path[i], shortest_path[i+1]) for i in range(len(shortest_path)-1)]
                    path_edge_set = set(path_edges + [(b,a) for a,b in path_edges])  # both directions
                    edge_counts = edge_counts[
                        edge_counts.apply(lambda row: (row['caller'], row['callee']) in path_edge_set, axis=1)
                    ]
            else:
                st.warning("⚠️ Path not found - nodes not in network or not connected")
        except nx.NetworkXNoPath:
            st.warning("⚠️ No path exists between these nodes")
        except Exception as e:
            st.error(f"❌ Path finding error: {e}")
    
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
    
    # Search/highlight filter
    highlighted_nodes = set()
    if search_query:
        all_nodes_list = list(set(edge_counts['caller'].tolist() + edge_counts['callee'].tolist()))
        highlighted_nodes = {n for n in all_nodes_list if search_query.lower() in n.lower()}
        if highlighted_nodes:
            st.info(f"🔍 Found {len(highlighted_nodes)} nodes matching '{search_query}'")
    
    # Limit max edges
    edge_counts = edge_counts.sort_values('count', ascending=False).head(max_edges)
    
    # Build NetworkX graph for community detection
    G = nx.from_pandas_edgelist(edge_counts, 'caller', 'callee', 'count')
    
    # Community detection
    communities = {}
    if color_by_cluster and len(G.nodes()) > 1:
        try:
            partition = community_louvain.best_partition(G.to_undirected())
            communities = partition
            num_communities = len(set(partition.values()))
            st.info(f"🔍 Found {num_communities} communities using Louvain algorithm")
        except Exception as e:
            st.warning(f"⚠️ Community detection failed: {e}")
    
    # Generate community colors
    community_colors = {}
    if communities:
        import matplotlib.cm as cm
        import matplotlib.colors as mcolors
        unique_communities = list(set(communities.values()))
        colors = cm.Set3(range(len(unique_communities)))
        for i, comm in enumerate(unique_communities):
            community_colors[comm] = mcolors.to_hex(colors[i])
    
    # Process node images
    image_data = {}
    if uploaded_images:
        for uploaded_file in uploaded_images:
            # Extract phone number from filename (remove extension)
            phone_number = uploaded_file.name.split('.')[0]
            # Convert to base64 data URI
            file_bytes = uploaded_file.read()
            b64_image = base64.b64encode(file_bytes).decode()
            file_ext = uploaded_file.name.split('.')[-1].lower()
            mime_type = f"image/{file_ext}"
            if file_ext == 'jpg':
                mime_type = "image/jpeg"
            data_uri = f"data:{mime_type};base64,{b64_image}"
            image_data[phone_number] = data_uri
        
        if image_data:
            st.success(f"📷 Loaded {len(image_data)} node images")
    
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
    
    # Build PyVis network with enhanced options
    net = Network(height="90vh", width="100%", directed=True)
    
    # Physics and interaction options
    physics_enabled = enable_physics_temp and not freeze_positions
    options = {
        "physics": {
            "enabled": physics_enabled
        },
        "stabilization": {
            "iterations": 0 if freeze_positions else 100
        },
        "interaction": {
            "dragNodes": True
        },
        "edges": {"smooth": True},
        "nodes": {"chosen": True}
    }
    if not show_labels:
        options["nodes"]["font"] = {"size": 0}
    
    net.set_options(json.dumps(options))
    
    # Show toolbar if requested
    if show_toolbar:
        net.show_buttons(['physics','interaction','layout','nodes','edges'])
    
    # Add nodes with enhanced styling
    for n, wt in node_weights.items():
        # Determine node class and color
        if n in path_nodes:
            node_class = "path"
            color = "#ff6b35"  # Orange for path nodes
        elif focus_number and n == focus_number:
            node_class = "target"
            color = target_color
        elif focus_number and n in focus_set and n != focus_number:
            node_class = "neighbor"
            color = neighbor_color
        elif n in highlighted_nodes:
            node_class = "highlighted"
            color = "#ff1744"  # Red for search matches
        elif color_by_cluster and n in communities:
            node_class = "community"
            color = community_colors.get(communities[n], primary_color)
        else:
            node_class = "primary"
            color = primary_color
        
        label = n if show_labels else ""
        size = _scale(wt, min_wt, max_wt, min_size, max_size)
        
        # Node properties
        node_props = {
            'label': label,
            'size': size,
            'color': color,
            'physics': not freeze_positions,
            'fixed': {'x': freeze_positions, 'y': freeze_positions} if freeze_positions else False
        }
        
        # Add image if available
        if n in image_data:
            node_props['shape'] = 'circularImage'
            node_props['image'] = image_data[n]
        
        net.add_node(n, **node_props)
    
    # Add edges with enhanced styling
    for _, row in edge_counts.iterrows():
        width = _scale(row['count'], min_count, max_count, 1, 10)
        
        # Edge color based on mode
        if edge_color_mode == "by weight":
            # Color by weight (blue to red gradient)
            weight_ratio = (row['count'] - min_count) / max(1, max_count - min_count)
            red = int(weight_ratio * 255)
            blue = int((1 - weight_ratio) * 255)
            edge_color = f"rgb({red}, 0, {blue})"
        elif edge_color_mode == "single color":
            edge_color = "#90caf9"
        else:  # inbound vs outbound (focus)
            if focus_number:
                if row['caller'] == focus_number:
                    edge_color = "#4caf50"  # Green for outbound
                elif row['callee'] == focus_number:
                    edge_color = "#f44336"  # Red for inbound
                else:
                    edge_color = "#90caf9"  # Blue for others
            else:
                edge_color = "#90caf9"
        
        net.add_edge(
            str(row['caller']), 
            str(row['callee']), 
            value=width, 
            title=f"Calls: {row['count']}", 
            color=edge_color
        )
    
    # Create legend
    if show_legend:
        st.markdown("---")
        st.subheader("🎨 Network Legend")
        
        legend_cols = st.columns(3)
        
        with legend_cols[0]:
            st.markdown("**Node Types:**")
            if path_nodes:
                st.markdown(f'<div style="display:flex;align-items:center;"><div style="width:20px;height:20px;background-color:#ff6b35;border-radius:50%;margin-right:10px;"></div>Path Nodes</div>', unsafe_allow_html=True)
            if focus_number:
                st.markdown(f'<div style="display:flex;align-items:center;"><div style="width:20px;height:20px;background-color:{target_color};border-radius:50%;margin-right:10px;"></div>Target Node</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="display:flex;align-items:center;"><div style="width:20px;height:20px;background-color:{neighbor_color};border-radius:50%;margin-right:10px;"></div>Neighbor Nodes</div>', unsafe_allow_html=True)
            if highlighted_nodes:
                st.markdown(f'<div style="display:flex;align-items:center;"><div style="width:20px;height:20px;background-color:#ff1744;border-radius:50%;margin-right:10px;"></div>Search Matches</div>', unsafe_allow_html=True)
            if not (path_nodes or focus_number or highlighted_nodes or communities):
                st.markdown(f'<div style="display:flex;align-items:center;"><div style="width:20px;height:20px;background-color:{primary_color};border-radius:50%;margin-right:10px;"></div>Regular Nodes</div>', unsafe_allow_html=True)
        
        with legend_cols[1]:
            st.markdown("**Edge Colors:**")
            if edge_color_mode == "by weight":
                st.markdown('🔵 Low Weight → 🔴 High Weight')
            elif edge_color_mode == "single color":
                st.markdown('🔵 All edges same color')
            elif focus_number:
                st.markdown('🟢 Outbound from target')
                st.markdown('🔴 Inbound to target')
                st.markdown('🔵 Other connections')
        
        with legend_cols[2]:
            if communities:
                st.markdown("**Communities:**")
                displayed_communities = list(set(communities.values()))[:8]  # Show max 8
                for comm in displayed_communities:
                    color = community_colors.get(comm, primary_color)
                    st.markdown(f'<div style="display:flex;align-items:center;"><div style="width:20px;height:20px;background-color:{color};border-radius:50%;margin-right:10px;"></div>Community {comm}</div>', unsafe_allow_html=True)
                if len(set(communities.values())) > 8:
                    st.markdown("... and more")
    
    # Network statistics
    st.markdown("---")
    st.subheader("📊 Network Statistics")
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.metric("Nodes", len(node_weights))
    with stat_cols[1]:
        st.metric("Edges", len(edge_counts))
    with stat_cols[2]:
        st.metric("Total Calls", edge_counts['count'].sum())
    with stat_cols[3]:
        if communities:
            st.metric("Communities", len(set(communities.values())))
        else:
            st.metric("Max Calls/Edge", edge_counts['count'].max())
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


import streamlit as st
from cdr_toolkit.ui import render_ribbon

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
	st.warning(f"Louvain community detection not available. Install with: pip install python-louvain\nError: {e}")
	LOUVAIN_OK = False



# Render the sticky ribbon navigation
render_ribbon(active="graphs", subtitle="Network Explorer")

# ...existing code for the Graphs page...

# Before rendering the graph, check PyVis
if not PYVIS_OK:
	st.stop()

# ...existing code for graph construction...

# Example Louvain usage (wrap with LOUVAIN_OK):
# if LOUVAIN_OK:
#     # Louvain community detection code here
# else:
#     st.info("Louvain community detection is not available.")

# ...existing code for the Graphs page...

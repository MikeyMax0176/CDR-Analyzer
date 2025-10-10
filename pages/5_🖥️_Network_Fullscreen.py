import streamlit as st
import streamlit.components.v1 as components
import os

# Set wide layout and page config for full-screen experience
st.set_page_config(
    layout="wide",
    page_title="CDR Network - Full Screen",
    page_icon="🖥️"
)

st.title("🖥️ CDR Network - Full Screen View")

# Check if network file exists
network_file = "cdr_network.html"
if os.path.exists(network_file):
    try:
        with open(network_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        st.info("💡 **Tip**: This is a full-screen view. Drag nodes to rearrange them - they'll stay where you drop them!")
        
        # Embed the network at full viewport height
        components.html(html_content, height=800, scrolling=False)
        
        # Download button
        st.download_button(
            "📥 Download Network HTML", 
            html_content, 
            network_file, 
            mime="text/html"
        )
        
    except Exception as e:
        st.error(f"Error loading network file: {e}")
else:
    st.warning("⚠️ No network file found. Please generate a network first in the Network Explorer page.")
    st.page_link("pages/4_🌐_Network_Explorer.py", label="← Go to Network Explorer")
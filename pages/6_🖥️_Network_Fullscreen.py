import streamlit as st
import streamlit.components.v1 as components
import base64
import os

st.title("🖥️ CDR Network - Full Screen View")

# Check for network HTML in session state first (preferred)
if "last_net_html" in st.session_state and st.session_state["last_net_html"]:
    html_content = st.session_state["last_net_html"]
    
    # Build data URL for new tab opening
    encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    data_url = f"data:text/html;base64,{encoded}"
    
    # Auto-open in new tab via JavaScript
    st.markdown(f"""
    <script>
    setTimeout(function() {{
        window.open('{data_url}', '_blank');
    }}, 1000);
    </script>
    """, unsafe_allow_html=True)
    
    st.success("� **Opening network in new tab...** (Wait 1 second)")
    st.info("💡 **If popup was blocked**, use the link below:")
    
    # Fallback link if popups are blocked
    st.markdown(f'<a href="{data_url}" target="_blank" rel="noopener noreferrer">🔗 Click here to open full-screen network</a>', unsafe_allow_html=True)
    
    # Also embed inline as backup
    st.markdown("---")
    st.subheader("📱 Embedded View (Backup)")
    components.html(html_content, height=800, scrolling=False)
    
    # Download button
    st.download_button("📥 Download Network HTML", html_content, "cdr_network.html", mime="text/html")

# Fallback: check if network file exists on disk
elif os.path.exists("cdr_network.html"):
    try:
        with open("cdr_network.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        st.info(
            "💡 **Tip**: This is a full-screen view. Drag nodes to rearrange them - they'll stay where you drop them!"
        )

        # Embed the network at full viewport height
        components.html(html_content, height=800, scrolling=False)

        # Download button
        st.download_button("📥 Download Network HTML", html_content, "cdr_network.html", mime="text/html")

    except Exception as e:
        st.error(f"Error loading network file: {e}")
else:
    st.warning(
        "⚠️ No network available. Please generate a network first in the Network Explorer page."
    )
    st.page_link("pages/4_🌐_Network_Explorer.py", label="← Go to Network Explorer")

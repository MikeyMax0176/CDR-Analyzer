import subprocess
from datetime import datetime, timezone


def render_snapshot_button():
    if st.button("💾 Snapshot Workspace State"):
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        cmd = f'git add -A && git commit -m "snapshot: {ts}" && git push'
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                st.success(f"Snapshot committed and pushed at {ts}")
            else:
                st.error(f"Snapshot failed: {result.stderr}")
        except Exception as e:
            st.error(f"Snapshot error: {e}")


import streamlit as st
from urllib.parse import urlencode


def render_ribbon(active, subtitle=None):
    """
    Render a sticky top navigation ribbon with active tab highlight and optional subtitle.
    Tabs: Ingest, Tables, Graphs, Maps, Reports
    """
    tabs = [
        ("ingest", "Ingest", "./pages/1_📥_Ingest_&_Map_Schema.py"),
        ("tables", "Tables", "./pages/2_🗃️_Datasets_&_Filters.py"),
        ("graphs", "Graphs", "./pages/4_🌐_Network_Explorer.py"),
        ("maps", "Maps", "./pages/6_🗺️_Geofence_&_Pins.py"),
        ("reports", "Reports", "./pages/7_📑_Reports.py"),
    ]
    st.markdown(
        """
    <style>
    .cdr-ribbon {
        position: sticky;
        top: 0;
        z-index: 1000;
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        gap: 2rem;
        padding: 0.5rem 1rem 0.5rem 0.5rem;
        border-bottom: 1px solid #eee;
        margin-bottom: 1.5rem;
    }
    .cdr-ribbon a {
        text-decoration: none;
        color: #444;
        font-weight: 500;
        font-size: 1.1rem;
        padding: 0.3rem 1.1rem;
        border-radius: 1.5rem;
        transition: background 0.2s, color 0.2s;
    }
    .cdr-ribbon a.active {
        background: #1976d2;
        color: #fff;
        font-weight: 700;
        box-shadow: 0 2px 8px #1976d233;
    }
    .cdr-ribbon a:hover {
        background: #e3f2fd;
        color: #1976d2;
    }
    .cdr-ribbon .cdr-subtitle {
        margin-left: auto;
        font-size: 1.05rem;
        color: #555;
        font-weight: 400;
        padding-right: 1.5rem;
        font-style: italic;
        letter-spacing: 0.01em;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
    nav_html = '<nav class="cdr-ribbon">'
    for key, label, page in tabs:
        active_class = "active" if key == active else ""
        nav_html += f'<a href="{page}" class="{active_class}">{label}</a>'
    if subtitle:
        nav_html += f'<span class="cdr-subtitle">{subtitle}</span>'
    nav_html += "</nav>"
    st.markdown(nav_html, unsafe_allow_html=True)
    st.markdown(
        """
    <script>
    document.addEventListener('keydown', function(e) {
        if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
        if (e.key >= '1' && e.key <= '5') {
            let links = document.querySelectorAll('.cdr-ribbon a');
            let idx = parseInt(e.key) - 1;
            if (links[idx]) links[idx].click();
        }
    });
    </script>
    """,
        unsafe_allow_html=True,
    )

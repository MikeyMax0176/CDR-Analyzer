import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from datetime import datetime
from cdr_toolkit.storage import (
    init_case_schema, ensure_case, list_cases,
    add_pin, list_pins, add_geofence, list_geofences,
    add_event, list_events
)

# Initialize case schema
if 'engine' not in st.session_state:
    st.session_state.engine = "cdr_toolkit.db"
init_case_schema(st.session_state.engine)

st.set_page_config(page_title="Geofence & Pins", page_icon="🗺️", layout="wide")
st.title("🗺️ Geofence & Pins")

# Sidebar - Controls
with st.sidebar:
    st.header("🎛️ Map Controls")
    
    # Case selector
    st.subheader("📋 Case Management")
    cases = list_cases(st.session_state.engine)
    case_options = {f"{case['name']} (ID: {case['id']})": case for case in cases}
    
    if case_options:
        selected_case_label = st.selectbox("Select Case", list(case_options.keys()))
        selected_case = case_options[selected_case_label]
        current_case_id = selected_case['id']
        st.info(f"📁 **{selected_case['name']}**")
    else:
        st.warning("No cases found. Create one in Cases page.")
        current_case_id = None
        selected_case = None
    
    # Create new case option
    with st.expander("➕ Quick Create Case"):
        with st.form("quick_case"):
            quick_case_name = st.text_input("Case Name")
            quick_case_desc = st.text_input("Description")
            if st.form_submit_button("Create"):
                if quick_case_name:
                    try:
                        case_id = ensure_case(st.session_state.engine, quick_case_name, quick_case_desc)
                        st.success(f"✅ Created: {quick_case_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
    
    # Map settings
    st.subheader("🗺️ Map Settings")
    center_lat = st.number_input("Center Latitude", value=37.7749, format="%.6f")
    center_lon = st.number_input("Center Longitude", value=-122.4194, format="%.6f")
    zoom_level = st.slider("Zoom Level", 1, 18, 10)
    
    # Pin settings
    st.subheader("📍 Pin Settings")
    pin_name_template = st.text_input("Pin Name Template", value="Pin {counter}")
    pin_color = st.selectbox("Pin Color", ["blue", "red", "green", "purple", "orange", "darkred", "lightred", "beige", "darkblue", "darkgreen", "cadetblue", "darkpurple", "white", "pink", "lightblue", "lightgreen", "gray", "black", "lightgray"])
    pin_icon = st.selectbox("Pin Icon", ["info-sign", "home", "star", "flag", "phone", "car", "camera", "warning-sign", "question-sign", "user", "time", "road", "map-marker"])
    
    # Event creation from map clicks
    st.subheader("🎯 Event Creation")
    create_event_on_click = st.checkbox("Create event on map click", value=False)
    if create_event_on_click:
        event_type = st.selectbox("Event Type", [
            "Location", "Surveillance", "Meeting", "Call", "SMS", 
            "Investigation", "Evidence", "Interview", "Other"
        ])
        event_title_template = st.text_input("Event Title Template", value="Location Event {counter}")

# Main map area
if current_case_id:
    # Get existing pins and geofences for this case
    pins = list_pins(st.session_state.engine, current_case_id)
    geofences = list_geofences(st.session_state.engine, current_case_id)
    events = list_events(st.session_state.engine, current_case_id)
    
    # Create folium map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_level)
    
    # Add existing pins
    for pin in pins:
        folium.Marker(
            [pin['latitude'], pin['longitude']],
            popup=f"<b>{pin['name']}</b><br>{pin['description']}<br><small>Created: {pin['created_at']}</small>",
            tooltip=pin['name'],
            icon=folium.Icon(color=pin['color'], icon=pin['icon'])
        ).add_to(m)
    
    # Add existing geofences
    for geofence in geofences:
        if geofence['coordinates']:
            if geofence['radius']:
                # Circle geofence
                center = geofence['coordinates'][0]  # Assume first coord is center
                folium.Circle(
                    center,
                    radius=geofence['radius'],
                    popup=f"<b>{geofence['name']}</b><br>Radius: {geofence['radius']}m<br><small>Created: {geofence['created_at']}</small>",
                    color=geofence['color'],
                    fill=True,
                    fillOpacity=0.2
                ).add_to(m)
            else:
                # Polygon geofence
                folium.Polygon(
                    geofence['coordinates'],
                    popup=f"<b>{geofence['name']}</b><br><small>Created: {geofence['created_at']}</small>",
                    color=geofence['color'],
                    fill=True,
                    fillOpacity=0.2
                ).add_to(m)
    
    # Add case events with location data
    location_events = [e for e in events if e['latitude'] and e['longitude']]
    for event in location_events:
        # Create different marker styles for different event types
        if event['event_type'] == 'Call':
            marker_color = 'green'
            marker_icon = 'phone'
        elif event['event_type'] == 'SMS':
            marker_color = 'blue'
            marker_icon = 'envelope'
        elif event['event_type'] == 'Meeting':
            marker_color = 'purple'
            marker_icon = 'user'
        elif event['event_type'] == 'Surveillance':
            marker_color = 'red'
            marker_icon = 'camera'
        else:
            marker_color = 'orange'
            marker_icon = 'info-sign'
        
        popup_content = f"""
        <b>{event['event_type']}: {event['title']}</b><br>
        {event['description']}<br>
        <b>Time:</b> {event['event_time'] or 'Not specified'}<br>
        """
        if event['phone_numbers']:
            popup_content += f"<b>Numbers:</b> {', '.join(event['phone_numbers'])}<br>"
        if event['tags']:
            popup_content += f"<b>Tags:</b> {', '.join(event['tags'])}<br>"
        popup_content += f"<small>Created: {event['created_at']}</small>"
        
        folium.Marker(
            [event['latitude'], event['longitude']],
            popup=popup_content,
            tooltip=f"{event['event_type']}: {event['title']}",
            icon=folium.Icon(color=marker_color, icon=marker_icon)
        ).add_to(m)
    
    # Display map and capture interactions
    map_data = st_folium(m, width=None, height=600, returned_objects=["last_clicked"])
    
    # Handle map clicks
    if map_data['last_clicked'] is not None:
        clicked_lat = map_data['last_clicked']['lat']
        clicked_lon = map_data['last_clicked']['lng']
        
        st.success(f"📍 Clicked: {clicked_lat:.6f}, {clicked_lon:.6f}")
        
        # Action buttons for the clicked location
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📍 Add Pin Here"):
                try:
                    # Generate pin name
                    pin_counter = len(pins) + 1
                    pin_name = pin_name_template.format(counter=pin_counter)
                    
                    pin_id = add_pin(
                        st.session_state.engine, current_case_id, pin_name,
                        clicked_lat, clicked_lon, pin_icon, pin_color,
                        f"Pin added at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    st.success(f"✅ Pin added: {pin_name} (ID: {pin_id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error adding pin: {e}")
        
        with col2:
            if st.button("🚧 Add Circular Geofence"):
                try:
                    # Generate geofence name
                    geofence_counter = len(geofences) + 1
                    geofence_name = f"Geofence {geofence_counter}"
                    
                    # Default 100m radius
                    geofence_id = add_geofence(
                        st.session_state.engine, current_case_id, geofence_name,
                        [[clicked_lat, clicked_lon]], 100, '#ff0000'
                    )
                    st.success(f"✅ Geofence added: {geofence_name} (ID: {geofence_id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error adding geofence: {e}")
        
        with col3:
            if create_event_on_click and st.button("🎯 Create Event Here"):
                try:
                    # Generate event title
                    event_counter = len(location_events) + 1
                    event_title = event_title_template.format(counter=event_counter)
                    
                    from cdr_toolkit.storage import add_event
                    event_id = add_event(
                        st.session_state.engine, current_case_id, event_type, event_title,
                        f"Event created from map click at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        datetime.now().isoformat(), clicked_lat, clicked_lon
                    )
                    st.success(f"✅ Event added: {event_title} (ID: {event_id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error adding event: {e}")
    
    # Statistics and management
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📍 Pins", len(pins))
    with col2:
        st.metric("🚧 Geofences", len(geofences))
    with col3:
        st.metric("🎯 Location Events", len(location_events))
    with col4:
        st.metric("📊 Total Events", len(events))
    
    # Management tabs
    tab1, tab2, tab3 = st.tabs(["📍 Manage Pins", "🚧 Manage Geofences", "🎯 Location Events"])
    
    with tab1:
        if pins:
            st.subheader("📍 Existing Pins")
            for pin in pins:
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**{pin['name']}**")
                        st.markdown(f"{pin['description']}")
                    with col2:
                        st.markdown(f"📍 {pin['latitude']:.4f}, {pin['longitude']:.4f}")
                        st.markdown(f"🎨 {pin['color']} / {pin['icon']}")
                    with col3:
                        st.markdown(f"🕒 {pin['created_at']}")
                    st.markdown("---")
        else:
            st.info("No pins for this case. Click on the map to add pins.")
    
    with tab2:
        if geofences:
            st.subheader("🚧 Existing Geofences")
            for geofence in geofences:
                with st.container():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**{geofence['name']}**")
                        if geofence['radius']:
                            center = geofence['coordinates'][0]
                            st.markdown(f"📍 Center: {center[0]:.4f}, {center[1]:.4f}")
                            st.markdown(f"📏 Radius: {geofence['radius']}m")
                        else:
                            st.markdown(f"📐 Polygon with {len(geofence['coordinates'])} points")
                    with col2:
                        st.markdown(f"🎨 {geofence['color']}")
                        st.markdown(f"🕒 {geofence['created_at']}")
                    st.markdown("---")
        else:
            st.info("No geofences for this case. Click on the map to add geofences.")
    
    with tab3:
        if location_events:
            st.subheader("🎯 Events with Location Data")
            for event in location_events:
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**{event['event_type']}: {event['title']}**")
                        st.markdown(f"{event['description']}")
                    with col2:
                        st.markdown(f"📍 {event['latitude']:.4f}, {event['longitude']:.4f}")
                        if event['phone_numbers']:
                            st.markdown(f"📞 {', '.join(event['phone_numbers'])}")
                    with col3:
                        st.markdown(f"🕒 {event['event_time'] or 'Not specified'}")
                        if event['tags']:
                            tag_text = " ".join([f"`{tag}`" for tag in event['tags']])
                            st.markdown(f"🏷️ {tag_text}")
                    st.markdown("---")
        else:
            st.info("No location events for this case. Add events with coordinates in the Cases page or enable 'Create event on click'.")

else:
    st.info("👈 Please select a case from the sidebar to manage geofences and pins.")
    
    # Show a default map without interaction
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_level)
    st_folium(m, width=None, height=400)

# Footer
st.markdown("---")
st.markdown("""
**💡 Tips:**
- **Pins**: Mark specific locations of interest (addresses, meeting points, evidence locations)
- **Geofences**: Define areas of interest for analysis (neighborhoods, restricted zones)
- **Events**: Create timestamped events with location data for comprehensive case tracking
- **Case Integration**: All pins, geofences, and events are linked to your selected case
- **Map Interactions**: Click anywhere on the map to add pins, geofences, or events
""")
import streamlit as st
import pandas as pd
from datetime import datetime, date
from cdr_toolkit.storage import (
    init_case_schema, ensure_case, list_cases, 
    add_note, list_notes, add_event, list_events,
    add_pin, list_pins, add_geofence, list_geofences
)

# Initialize case schema
if 'engine' not in st.session_state:
    st.session_state.engine = "cdr_toolkit.db"
init_case_schema(st.session_state.engine)

st.set_page_config(page_title="Cases, Notes & Events", page_icon="🗂️", layout="wide")
st.title("🗂️ Cases, Notes & Events")

# Sidebar - Case Management
with st.sidebar:
    st.header("📋 Case Management")
    
    # Case selector
    cases = list_cases(st.session_state.engine)
    case_options = {f"{case['name']} (ID: {case['id']})": case for case in cases}
    
    if case_options:
        selected_case_label = st.selectbox("Select Case", list(case_options.keys()))
        selected_case = case_options[selected_case_label]
        current_case_id = selected_case['id']
        st.info(f"📁 **{selected_case['name']}**\n\n{selected_case['description']}")
    else:
        st.warning("No cases found. Create one below.")
        current_case_id = None
        selected_case = None
    
    # Create new case
    st.subheader("➕ Create New Case")
    with st.form("create_case"):
        new_case_name = st.text_input("Case Name", placeholder="Investigation Alpha")
        new_case_desc = st.text_area("Description", placeholder="Brief description of the case...")
        
        if st.form_submit_button("Create Case"):
            if new_case_name:
                try:
                    case_id = ensure_case(st.session_state.engine, new_case_name, new_case_desc)
                    st.success(f"✅ Created case: {new_case_name} (ID: {case_id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating case: {e}")
            else:
                st.error("Case name is required")

# Main content - only show if case is selected
if current_case_id:
    # Create three main tabs
    tab1, tab2, tab3 = st.tabs(["📝 Notes", "🎯 Events", "📊 Overview"])
    
    with tab1:
        st.subheader(f"📝 Notes for {selected_case['name']}")
        
        # Add new note
        with st.expander("➕ Add New Note", expanded=False):
            with st.form("add_note"):
                note_title = st.text_input("Note Title", placeholder="Meeting notes, observation, etc.")
                note_content = st.text_area("Content", placeholder="Detailed note content...", height=150)
                
                if st.form_submit_button("Save Note"):
                    if note_title and note_content:
                        try:
                            note_id = add_note(st.session_state.engine, current_case_id, note_title, note_content)
                            st.success(f"✅ Note saved (ID: {note_id})")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error saving note: {e}")
                    else:
                        st.error("Both title and content are required")
        
        # Display existing notes
        notes = list_notes(st.session_state.engine, current_case_id)
        if notes:
            for note in notes:
                with st.container():
                    st.markdown(f"**{note['title']}** *({note['created_at']})*")
                    st.markdown(note['content'])
                    st.markdown("---")
        else:
            st.info("No notes found for this case. Add your first note above.")
    
    with tab2:
        st.subheader(f"🎯 Events for {selected_case['name']}")
        
        # Add new event
        with st.expander("➕ Add New Event", expanded=False):
            with st.form("add_event"):
                col1, col2 = st.columns(2)
                
                with col1:
                    event_type = st.selectbox("Event Type", [
                        "Call", "SMS", "Location", "Meeting", "Surveillance", 
                        "Investigation", "Evidence", "Interview", "Other"
                    ])
                    event_title = st.text_input("Title", placeholder="Brief event title")
                    event_date = st.date_input("Event Date", value=datetime.now().date())
                    event_time_val = st.time_input("Event Time", value=datetime.now().time())
                    import datetime as dt
                    event_time = dt.datetime.combine(event_date, event_time_val)
                
                with col2:
                    lat = st.number_input("Latitude (optional)", value=None, format="%.6f")
                    lon = st.number_input("Longitude (optional)", value=None, format="%.6f")
                    phone_numbers_text = st.text_input("Phone Numbers (comma-separated)", placeholder="123456789, 987654321")
                
                event_description = st.text_area("Description", placeholder="Detailed event description...", height=100)
                tags_text = st.text_input("Tags (comma-separated)", placeholder="urgent, evidence, follow-up")
                
                if st.form_submit_button("Save Event"):
                    if event_title:
                        try:
                            # Parse phone numbers and tags
                            phone_numbers = [p.strip() for p in phone_numbers_text.split(",") if p.strip()] if phone_numbers_text else []
                            tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []
                            
                            event_id = add_event(
                                st.session_state.engine, current_case_id, event_type, event_title,
                                event_description, event_time.isoformat(),
                                lat, lon, phone_numbers, tags
                            )
                            st.success(f"✅ Event saved (ID: {event_id})")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error saving event: {e}")
                    else:
                        st.error("Event title is required")
        
        # Display existing events
        events = list_events(st.session_state.engine, current_case_id)
        if events:
            # CSV download button
            events_df = pd.DataFrame(events)
            csv_data = events_df.to_csv(index=False)
            st.download_button(
                "📥 Download Events CSV",
                csv_data,
                f"{selected_case['name']}_events.csv",
                "text/csv"
            )
            
            # Display events
            for event in events:
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{event['event_type']}: {event['title']}**")
                        if event['description']:
                            st.markdown(event['description'])
                    
                    with col2:
                        if event['event_time']:
                            st.markdown(f"🕒 {event['event_time']}")
                        if event['latitude'] and event['longitude']:
                            st.markdown(f"📍 {event['latitude']:.4f}, {event['longitude']:.4f}")
                    
                    with col3:
                        if event['phone_numbers']:
                            st.markdown(f"📞 {', '.join(event['phone_numbers'])}")
                        if event['tags']:
                            tag_text = " ".join([f"`{tag}`" for tag in event['tags']])
                            st.markdown(f"🏷️ {tag_text}")
                    
                    st.markdown("---")
        else:
            st.info("No events found for this case. Add your first event above.")
    
    with tab3:
        st.subheader(f"📊 Overview for {selected_case['name']}")
        
        # Get all data for this case
        notes = list_notes(st.session_state.engine, current_case_id)
        events = list_events(st.session_state.engine, current_case_id)
        pins = list_pins(st.session_state.engine, current_case_id)
        geofences = list_geofences(st.session_state.engine, current_case_id)
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📝 Notes", len(notes))
        with col2:
            st.metric("🎯 Events", len(events))
        with col3:
            st.metric("📍 Pins", len(pins))
        with col4:
            st.metric("🚧 Geofences", len(geofences))
        
        # Case details
        st.markdown("### Case Information")
        st.markdown(f"**Name:** {selected_case['name']}")
        st.markdown(f"**Description:** {selected_case['description']}")
        st.markdown(f"**Created:** {selected_case['created_at']}")
        st.markdown(f"**Last Updated:** {selected_case['updated_at']}")
        
        # Recent activity
        if events:
            st.markdown("### Recent Events")
            recent_events = events[:5]  # Show last 5 events
            for event in recent_events:
                st.markdown(f"- **{event['event_type']}**: {event['title']} *({event['event_time'] or event['created_at']})*")
        
        # Event types breakdown
        if events:
            st.markdown("### Event Types")
            event_types = {}
            for event in events:
                event_type = event['event_type']
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            for event_type, count in sorted(event_types.items()):
                st.markdown(f"- **{event_type}**: {count}")
        
        # Phone numbers involved
        if events:
            all_phones = set()
            for event in events:
                all_phones.update(event['phone_numbers'])
            
            if all_phones:
                st.markdown("### Phone Numbers Involved")
                st.markdown(f"**Total unique numbers:** {len(all_phones)}")
                if len(all_phones) <= 20:  # Show if not too many
                    for phone in sorted(all_phones):
                        st.markdown(f"- {phone}")
                else:
                    st.markdown("*(Too many to display - see individual events)*")

else:
    st.info("👈 Please select or create a case from the sidebar to manage notes and events.")

# Footer with helpful information
st.markdown("---")
st.markdown("""
**💡 Tips:**
- **Notes**: Use for documenting meetings, observations, and general case information
- **Events**: Record specific incidents with timestamps, locations, and involved parties
- **Location Data**: Add GPS coordinates to events for mapping integration
- **Tags**: Use tags to categorize and filter events (e.g., 'urgent', 'evidence', 'follow-up')
- **Phone Numbers**: Associate phone numbers with events for CDR analysis integration
""")
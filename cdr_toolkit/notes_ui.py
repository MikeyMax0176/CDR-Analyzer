"""
Notes Widget UI Component for CDR Analyzer
Provides a reusable sidebar widget for creating and managing contextual notes
"""
import streamlit as st
import json
from typing import Callable, Tuple, Any, Dict
from cdr_toolkit.storage import (
    add_note_with_context, list_notes, update_note, delete_note, 
    migrate_notes_context, list_cases
)


def case_selector_sidebar():
    """Display a case selector in the sidebar and set active_case_id"""
    engine = st.session_state.get('engine', 'cdr_toolkit.db')
    
    with st.sidebar:
        st.markdown("---")
        st.subheader("📁 Active Case")
        
        cases = list_cases(engine)
        if cases:
            case_options = {f"{case['name']}": case['id'] for case in cases}
            
            # Get current selection or default to first
            current_case_name = None
            if 'active_case_id' in st.session_state:
                for case in cases:
                    if case['id'] == st.session_state['active_case_id']:
                        current_case_name = case['name']
                        break
            
            if current_case_name and current_case_name in case_options:
                default_index = list(case_options.keys()).index(current_case_name)
            else:
                default_index = 0
            
            selected_case_name = st.selectbox(
                "Select active case for notes",
                list(case_options.keys()),
                index=default_index,
                key="case_selector_sidebar"
            )
            
            st.session_state['active_case_id'] = case_options[selected_case_name]
            st.caption(f"Case ID: {st.session_state['active_case_id']}")
        else:
            st.info("No cases found. Create one in the Cases page.")
            if 'active_case_id' in st.session_state:
                del st.session_state['active_case_id']


def notes_widget(page_id: str, case_id: int, user: str = None, 
                make_context: Callable[[], Tuple[str, Dict, str, Any]] = None):
    """
    Render notes widget in sidebar with create form and recent notes list
    
    Args:
        page_id: Unique identifier for the current page (e.g., "stats", "network")
        case_id: Active case ID
        user: Current user identifier (optional)
        make_context: Function that returns (anchor, context_dict, page_file, query_data)
                     for capturing the current page state
    """
    if not case_id:
        return
    
    # Ensure migration has been run
    engine = st.session_state.get('engine', 'cdr_toolkit.db')
    
    with st.sidebar.expander("📝 Notes", expanded=False):
        st.markdown("### Create Note")
        
        # Note creation form
        note_content = st.text_area(
            "Note content", 
            placeholder="Add a note about this view...",
            key=f"note_content_{page_id}",
            height=100
        )
        
        tags_input = st.text_input(
            "Tags (comma-separated)",
            placeholder="analysis, important, follow-up",
            key=f"note_tags_{page_id}"
        )
        
        # Action buttons in columns
        col1, col2 = st.columns(2)
        
        with col1:
            save_btn = st.button("💾 Save", key=f"save_note_{page_id}")
        
        with col2:
            save_pin_btn = st.button("📌 Save+Pin", key=f"save_pin_note_{page_id}")
        
        # Handle save actions
        if save_btn or save_pin_btn:
            if note_content.strip():
                pinned = save_pin_btn
                _save(
                    engine=engine,
                    case_id=case_id,
                    page_id=page_id,
                    content=note_content,
                    tags_input=tags_input,
                    pinned=pinned,
                    make_context=make_context,
                    user=user
                )
                st.success("✅ Note saved!")
                # Clear form
                st.session_state[f"note_content_{page_id}"] = ""
                st.session_state[f"note_tags_{page_id}"] = ""
                st.rerun()
            else:
                st.error("Note content cannot be empty")
        
        # Display recent notes for this page
        st.markdown("---")
        st.markdown("### Recent Notes")
        
        notes = list_notes(engine, case_id=case_id, page_id=page_id)
        
        if notes:
            for note in notes[:10]:  # Show up to 10 most recent
                with st.container():
                    # Note header with pin indicator
                    pin_icon = "📌 " if note.get('pinned') else ""
                    st.markdown(f"**{pin_icon}Note #{note['id']}**")
                    
                    # Editable content
                    edited_content = st.text_area(
                        "Content",
                        value=note['content'],
                        key=f"edit_content_{note['id']}",
                        height=80,
                        label_visibility="collapsed"
                    )
                    
                    # Editable tags
                    current_tags = ", ".join(note.get('tags', []))
                    edited_tags = st.text_input(
                        "Tags",
                        value=current_tags,
                        key=f"edit_tags_{note['id']}",
                        placeholder="tags...",
                        label_visibility="collapsed"
                    )
                    
                    # Editable pinned status
                    edited_pinned = st.checkbox(
                        "Pinned",
                        value=note.get('pinned', False),
                        key=f"edit_pinned_{note['id']}"
                    )
                    
                    # Action buttons
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    with btn_col1:
                        if st.button("Update", key=f"update_{note['id']}"):
                            # Parse tags
                            tags_list = [t.strip() for t in edited_tags.split(",") if t.strip()]
                            
                            # Check if anything changed
                            content_changed = edited_content != note['content']
                            tags_changed = tags_list != note.get('tags', [])
                            pinned_changed = edited_pinned != note.get('pinned', False)
                            
                            if content_changed or tags_changed or pinned_changed:
                                update_note(
                                    engine, 
                                    note['id'],
                                    content=edited_content if content_changed else None,
                                    tags=tags_list if tags_changed else None,
                                    pinned=edited_pinned if pinned_changed else None
                                )
                                st.success("✅ Updated!")
                                st.rerun()
                            else:
                                st.info("No changes detected")
                    
                    with btn_col2:
                        if st.button("Delete", key=f"delete_{note['id']}"):
                            delete_note(engine, note['id'])
                            st.success("🗑️ Deleted!")
                            st.rerun()
                    
                    with btn_col3:
                        # Show "Open context" link if context is available
                        if note.get('link_url'):
                            st.markdown(
                                f"[🔗 Context]({note['link_url']})",
                                unsafe_allow_html=True
                            )
                        elif note.get('anchor'):
                            st.caption(f"🔗 {note['anchor']}")
                    
                    # Display metadata
                    st.caption(f"Created: {note['created_at']}")
                    if note.get('updated_at') and note['updated_at'] != note['created_at']:
                        st.caption(f"Updated: {note['updated_at']}")
                    
                    # Display tags as badges
                    if note.get('tags'):
                        tag_html = " ".join([f'<span style="background-color:#e0e0e0;padding:2px 6px;border-radius:3px;font-size:0.8em;margin-right:4px;">{tag}</span>' for tag in note['tags']])
                        st.markdown(tag_html, unsafe_allow_html=True)
                    
                    st.markdown("---")
        else:
            st.info("No notes yet. Create one above!")


def _save(engine, case_id: int, page_id: str, content: str, 
         tags_input: str, pinned: bool, make_context: Callable = None,
         user: str = None):
    """
    Internal function to save a note with context
    
    Args:
        engine: Database engine
        case_id: Case ID
        page_id: Page identifier
        content: Note content
        tags_input: Comma-separated tags string
        pinned: Whether to pin the note
        make_context: Function to capture current context
        user: User identifier
    """
    # Parse tags
    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
    
    # Capture context if available
    anchor = None
    context_json = None
    link_url = None
    
    if make_context:
        try:
            anchor, ctx_dict, page_file, query = make_context()
            if ctx_dict:
                context_json = json.dumps(ctx_dict)
            # Build link URL if possible
            if page_file and anchor:
                link_url = f"{page_file}#{anchor}"
        except Exception as e:
            # Don't fail if context capture fails
            st.warning(f"Could not capture context: {e}")
    
    # Save note
    add_note_with_context(
        engine=engine,
        case_id=case_id,
        content=content,
        page=page_id,
        anchor=anchor,
        context_json=context_json,
        link_url=link_url,
        tags=tags,
        pinned=pinned,
        user=user
    )

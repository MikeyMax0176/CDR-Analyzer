# Notes Feature Documentation

## Overview

The CDR Analyzer now includes a comprehensive notes system that allows analysts to capture observations, tag important findings, and maintain context-aware documentation throughout their investigations.

## Key Features

### 📝 Context-Aware Notes
- Notes are tied to specific pages (Stats, Network Explorer, Geofence & Pins)
- Each note captures the page context where it was created
- Notes are organized by case for investigation management

### 🏷️ Tag System
- Add multiple tags to notes (comma-separated)
- Visual tag badges for quick identification
- Useful for categorizing notes (e.g., "urgent", "follow-up", "evidence")

### 📌 Pin Important Notes
- Pin critical notes for priority display
- Pinned notes appear first in the list
- Visual indicator (📌) shows pinned status

### ✏️ Inline Editing
- Edit note content directly in the UI
- Update tags without recreating the note
- Toggle pinned status with a checkbox
- Changes saved with "Update" button

### 🗂️ Multi-Case Support
- Work with multiple investigations simultaneously
- Select active case via sidebar selector
- Notes automatically associated with active case

## Using the Notes System

### Step 1: Select a Case
Navigate to any analysis page and use the case selector in the sidebar:
```
📁 Active Case
Select active case for notes: [Investigation Alpha ▼]
```

### Step 2: Access Notes Widget
Expand the "📝 Notes" section in the sidebar.

### Step 3: Create Notes
1. Type your observation in the text area
2. (Optional) Add tags separated by commas
3. Click "💾 Save" or "📌 Save+Pin"

Example:
```
Note content: High call volume spike detected at 2 PM
Tags: analysis, temporal, important
[Click Save+Pin to mark as important]
```

### Step 4: Review and Manage Notes
- View recent notes for the current page
- Edit content, tags, or pinned status inline
- Click "Update" to save changes
- Click "Delete" to remove a note

## Database Schema

The notes table includes these columns:
- `id` - Unique identifier
- `case_id` - Associated case
- `content` - Note text
- `page` - Page identifier (stats_visuals, network_explorer, geofence_pins)
- `anchor` - Page-specific anchor
- `context_json` - JSON context data
- `link_url` - Link back to context
- `tags` - JSON array of tags
- `pinned` - Boolean flag (0/1)
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## API Reference

### Storage Functions

```python
from cdr_toolkit.storage import (
    migrate_notes_context,
    add_note_with_context,
    list_notes,
    get_note,
    update_note,
    delete_note
)

# Migration (idempotent)
migrate_notes_context(engine)

# Create note with context
note_id = add_note_with_context(
    engine, 
    case_id=1,
    content="Your note here",
    page="stats_visuals",
    tags=["important", "follow-up"],
    pinned=True
)

# List notes with filters
notes = list_notes(
    engine,
    case_id=1,              # Filter by case
    page_id="stats_visuals", # Filter by page
    pinned_only=True        # Show only pinned
)

# Get specific note
note = get_note(engine, note_id)

# Update note
update_note(
    engine,
    note_id,
    content="Updated content",
    tags=["new", "tags"],
    pinned=False
)

# Delete note
delete_note(engine, note_id)
```

### UI Components

```python
from cdr_toolkit.notes_ui import notes_widget, case_selector_sidebar

# Add case selector to sidebar
case_selector_sidebar()

# Define context capture (optional)
def make_context():
    context = {"key": "value"}
    return ("anchor-id", context, "pages/my_page.py", None)

# Render notes widget
if st.session_state.get('active_case_id'):
    notes_widget(
        page_id="my_page",
        case_id=st.session_state['active_case_id'],
        user=st.session_state.get('user'),
        make_context=make_context
    )
```

## Implementation Details

### Backward Compatibility
The system maintains backward compatibility with the original `add_note()` function. Existing notes will continue to work, with new fields defaulting to appropriate values.

### Data Safety
- Idempotent migrations prevent data loss on upgrades
- Transaction-safe database operations
- Proper error handling throughout
- No existing notes are modified during migration

### Performance
- Notes are fetched only when the widget is expanded
- Pagination limits display to 10 most recent notes per page
- Efficient SQLite queries with proper indexing via foreign keys

## Use Cases

### Scenario 1: Pattern Recognition
While reviewing stats, an analyst notices unusual call patterns:
```
Note: "Call volume spike 2-4 PM weekdays, consistent across 3 weeks"
Tags: pattern, temporal, investigation
Action: Pin for team review
```

### Scenario 2: Network Analysis
During network exploration, analyst identifies a hub:
```
Note: "555-0100 central hub, connects to 15 unique numbers"
Tags: network, hub, suspect
Action: Save and continue analysis
```

### Scenario 3: Follow-up Actions
Analyst marks items requiring further investigation:
```
Note: "Need to verify 555-0200 against database"
Tags: follow-up, verify, urgent
Action: Pin and assign
```

## Tips and Best Practices

1. **Use Descriptive Content**: Write clear, specific notes that will make sense later
2. **Tag Consistently**: Develop a tag vocabulary for your team (e.g., "urgent", "evidence", "follow-up")
3. **Pin Strategically**: Reserve pins for truly important notes to avoid clutter
4. **Page-Specific Notes**: Notes on different pages help organize observations by analysis type
5. **Regular Review**: Periodically review and update notes as investigation progresses
6. **Delete Outdated**: Remove notes that are no longer relevant to keep lists clean

## Troubleshooting

### Issue: No case selector visible
**Solution**: Create a case in the Cases, Notes & Events page first.

### Issue: Notes not saving
**Solution**: Ensure a case is selected in the sidebar case selector.

### Issue: Notes from old schema
**Solution**: Migration runs automatically. Old notes will have empty tags and unpinned status.

## Future Enhancements

Potential future improvements:
- Export notes to PDF/Word reports
- Search and filter notes across all cases
- Note templates for common observations
- Collaborative notes with user attribution
- Note linking and references
- Automated note generation from analysis results

## Support

For issues or questions:
1. Check this documentation
2. Review example usage in the analysis pages
3. Examine the test files for additional examples
4. Open an issue on GitHub

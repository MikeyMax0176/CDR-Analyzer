"""
Node Directory Management for CDR Analyzer
Handles persistence and restoration of node metadata (names, roles, photos, notes).
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


def _ensure_case_dir(case_id: str) -> Path:
    """Ensure the case directory exists and return its path."""
    case_dir = Path(".table_dancer/cases") / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def save_node_dir(case_id: str, data: Dict[str, Any]) -> bool:
    """
    Save node directory data to JSON file.
    
    Args:
        case_id: Unique identifier for the case
        data: Dictionary of node metadata keyed by normalized phone numbers
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        case_dir = _ensure_case_dir(case_id)
        file_path = case_dir / "node_directory.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error saving node directory: {e}")
        return False


def load_node_dir(case_id: str) -> Dict[str, Any]:
    """
    Load node directory data from JSON file.
    
    Args:
        case_id: Unique identifier for the case
        
    Returns:
        dict: Node metadata dictionary, empty if file doesn't exist or error occurs
    """
    try:
        case_dir = Path(".table_dancer/cases") / case_id
        file_path = case_dir / "node_directory.json"
        
        if not file_path.exists():
            return {}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Error loading node directory: {e}")
        return {}


def normalize_phone(phone: str) -> str:
    """Extract digits-only phone number for consistent keying."""
    return ''.join(c for c in str(phone) if c.isdigit())


def merge_node_data(existing: Dict[str, Any], csv_data: Dict[str, Any], image_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge node data with precedence: existing (manual edits) > csv_data > image_data
    
    Args:
        existing: Current node directory data
        csv_data: Data from uploaded CSV
        image_data: Data from uploaded images
        
    Returns:
        dict: Merged node directory
    """
    result = {}
    
    # Get all unique phone numbers
    all_phones = set(existing.keys()) | set(csv_data.keys()) | set(image_data.keys())
    
    for phone in all_phones:
        node_data = {
            "phone": phone,
            "name": "",
            "role": "",
            "photo_data_uri": "",
            "notes": ""
        }
        
        # Start with image data (lowest priority)
        if phone in image_data:
            node_data.update(image_data[phone])
            
        # Override with CSV data (medium priority)
        if phone in csv_data:
            for key, value in csv_data[phone].items():
                if value:  # Only override if CSV has non-empty value
                    node_data[key] = value
                    
        # Override with existing data (highest priority - manual edits)
        if phone in existing:
            for key, value in existing[phone].items():
                if value:  # Only override if existing has non-empty value
                    node_data[key] = value
                    
        result[phone] = node_data
    
    return result
"""
Node Directory Management for CDR Analyzer
Handles persistence and restoration of node metadata (names, roles, photos, notes).
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


def _ensure_case_dir(case_id: str) -> Path:
    """Ensure the case directory exists and return its path."""
    case_dir = Path(".table_dancer/cases") / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def save_node_dir(case_id: str, data: Dict[str, Any]) -> bool:
    """
    Save node directory data to JSON file.
    
    Args:
        case_id: Unique identifier for the case
        data: Dictionary of node metadata keyed by normalized phone numbers
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        case_dir = _ensure_case_dir(case_id)
        file_path = case_dir / "node_directory.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error saving node directory: {e}")
        return False


def load_node_dir(case_id: str) -> Dict[str, Any]:
    """
    Load node directory data from JSON file.
    
    Args:
        case_id: Unique identifier for the case
        
    Returns:
        dict: Node metadata dictionary, empty if file doesn't exist or error occurs
    """
    try:
        case_dir = Path(".table_dancer/cases") / case_id
        file_path = case_dir / "node_directory.json"
        
        if not file_path.exists():
            return {}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Error loading node directory: {e}")
        return {}


def normalize_phone(phone: str) -> str:
    """Extract digits-only phone number for consistent keying."""
    return ''.join(c for c in str(phone) if c.isdigit())


def merge_node_data(existing: Dict[str, Any], csv_data: Dict[str, Any], image_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge node data with precedence: existing (manual edits) > csv_data > image_data
    
    Args:
        existing: Current node directory data
        csv_data: Data from uploaded CSV
        image_data: Data from uploaded images
        
    Returns:
        dict: Merged node directory
    """
    result = {}
    
    # Get all unique phone numbers
    all_phones = set(existing.keys()) | set(csv_data.keys()) | set(image_data.keys())
    
    for phone in all_phones:
        node_data = {
            "phone": phone,
            "name": "",
            "role": "",
            "photo_data_uri": "",
            "notes": ""
        }
        
        # Start with image data (lowest priority)
        if phone in image_data:
            node_data.update(image_data[phone])
            
        # Override with CSV data (medium priority)
        if phone in csv_data:
            for key, value in csv_data[phone].items():
                if value:  # Only override if CSV has non-empty value
                    node_data[key] = value
                    
        # Override with existing data (highest priority - manual edits)
        if phone in existing:
            for key, value in existing[phone].items():
                if value:  # Only override if existing has non-empty value
                    node_data[key] = value
                    
        result[phone] = node_data
    
    return result
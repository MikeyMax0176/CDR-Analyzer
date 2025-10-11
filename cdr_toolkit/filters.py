import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date

def apply_filters(
    datasets: Dict[str, pd.DataFrame], 
    enabled_sources: List[str], 
    mute_numbers: List[str] = None, 
    time_range: Tuple[datetime, datetime] = None, 
    min_duration: float = 0, 
    tech_sel: List[str] = None
) -> pd.DataFrame:
    """
    Apply filters across multiple datasets and return a combined DataFrame.
    
    Args:
        datasets: Dictionary of dataset_name -> DataFrame
        enabled_sources: List of dataset names to include
        mute_numbers: List of phone numbers to exclude
        time_range: Tuple of (start_datetime, end_datetime) for filtering
        min_duration: Minimum call duration in seconds
        tech_sel: List of technologies to include (2G, 3G, 4G, 5G, etc.)
    
    Returns:
        Combined DataFrame with 'source' column and standardized 'ts' datetime column
    """
    combined_dfs = []
    
    for source_name in enabled_sources:
        if source_name not in datasets:
            continue
            
        df = datasets[source_name].copy()
        if df.empty:
            continue
        
        # Add source column
        df['source'] = source_name
        
        # Standardize timestamp column
        df = _standardize_timestamp(df)
        
        # Apply time range filter
        if time_range and 'ts' in df.columns:
            start_dt, end_dt = time_range
            df = df[(df['ts'] >= start_dt) & (df['ts'] <= end_dt)]
        
        # Apply mute numbers filter
        if mute_numbers:
            df = _apply_mute_filter(df, mute_numbers)
        
        # Apply minimum duration filter
        if min_duration > 0:
            df = _apply_duration_filter(df, min_duration)
        
        # Apply technology filter
        if tech_sel:
            df = _apply_technology_filter(df, tech_sel)
        
        if not df.empty:
            combined_dfs.append(df)
    
    if not combined_dfs:
        # Return empty DataFrame with required columns
        return pd.DataFrame(columns=['source', 'ts'])
    
    # Combine all datasets
    combined_df = pd.concat(combined_dfs, ignore_index=True, sort=False)
    
    # Sort by timestamp if available
    if 'ts' in combined_df.columns:
        combined_df = combined_df.sort_values('ts').reset_index(drop=True)
    
    return combined_df

def _standardize_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a standardized 'ts' timestamp column from common timestamp column names.
    """
    timestamp_cols = [
        'timestamp', 'ts', 'datetime', 'start_time', 'call_time', 
        'event_time', 'time', 'date_time', 'call_start', 'start_dt'
    ]
    
    # Find the first available timestamp column
    ts_col = None
    for col in timestamp_cols:
        if col in df.columns:
            ts_col = col
            break
    
    if ts_col and ts_col != 'ts':
        # Convert to datetime and create 'ts' column
        try:
            df['ts'] = pd.to_datetime(df[ts_col], errors='coerce', utc=True).dt.tz_convert(None)
        except Exception:
            # If conversion fails, try without UTC
            try:
                df['ts'] = pd.to_datetime(df[ts_col], errors='coerce')
            except Exception:
                pass
    elif ts_col == 'ts':
        # Ensure ts column is datetime
        try:
            df['ts'] = pd.to_datetime(df['ts'], errors='coerce')
        except Exception:
            pass
    
    return df

def _apply_mute_filter(df: pd.DataFrame, mute_numbers: List[str]) -> pd.DataFrame:
    """
    Remove rows containing any of the muted phone numbers.
    """
    if not mute_numbers:
        return df
    
    # Common phone number columns
    phone_cols = [
        'caller', 'callee', 'calling_number', 'called_number', 
        'a_number', 'b_number', 'msisdn', 'phone_number', 'number'
    ]
    
    # Create filter mask
    mask = pd.Series([True] * len(df), index=df.index)
    
    for col in phone_cols:
        if col in df.columns:
            # Convert to string and check if any muted number is contained
            col_str = df[col].astype(str)
            for mute_num in mute_numbers:
                mask &= ~col_str.str.contains(str(mute_num), na=False)
    
    return df[mask]

def _apply_duration_filter(df: pd.DataFrame, min_duration: float) -> pd.DataFrame:
    """
    Filter rows by minimum call duration.
    """
    duration_cols = [
        'duration', 'call_duration', 'dur', 'length', 
        'talk_time', 'connection_time', 'call_length'
    ]
    
    for col in duration_cols:
        if col in df.columns:
            try:
                # Convert to numeric and filter
                duration_numeric = pd.to_numeric(df[col], errors='coerce')
                return df[duration_numeric >= min_duration]
            except Exception:
                continue
    
    # If no duration column found, return original dataframe
    return df

def _apply_technology_filter(df: pd.DataFrame, tech_sel: List[str]) -> pd.DataFrame:
    """
    Filter rows by technology type (2G, 3G, 4G, 5G, etc.).
    """
    tech_cols = [
        'technology', 'tech', 'network_type', 'radio_type', 
        'access_tech', 'rat', 'network', 'tech_type'
    ]
    
    for col in tech_cols:
        if col in df.columns:
            # Create case-insensitive filter
            col_upper = df[col].astype(str).str.upper()
            tech_upper = [t.upper() for t in tech_sel]
            
            # Check for exact matches or partial matches (e.g., "4G" in "LTE/4G")
            mask = pd.Series([False] * len(df), index=df.index)
            for tech in tech_upper:
                mask |= col_upper.str.contains(tech, na=False)
            
            return df[mask]
    
    # If no technology column found, return original dataframe
    return df

def get_dataset_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get summary statistics for a dataset.
    """
    summary = {
        'total_rows': len(df),
        'date_range': None,
        'unique_callers': 0,
        'unique_callees': 0,
        'total_duration': 0,
        'technologies': [],
        'sources': []
    }
    
    if df.empty:
        return summary
    
    # Date range
    if 'ts' in df.columns:
        ts_valid = df['ts'].dropna()
        if not ts_valid.empty:
            summary['date_range'] = (ts_valid.min(), ts_valid.max())
    
    # Phone number counts
    if 'caller' in df.columns:
        summary['unique_callers'] = df['caller'].nunique()
    if 'callee' in df.columns:
        summary['unique_callees'] = df['callee'].nunique()
    
    # Total duration
    duration_cols = ['duration', 'call_duration', 'dur']
    for col in duration_cols:
        if col in df.columns:
            try:
                duration_sum = pd.to_numeric(df[col], errors='coerce').sum()
                summary['total_duration'] = duration_sum
                break
            except Exception:
                continue
    
    # Technologies
    tech_cols = ['technology', 'tech', 'network_type']
    for col in tech_cols:
        if col in df.columns:
            summary['technologies'] = df[col].value_counts().head(10).to_dict()
            break
    
    # Sources
    if 'source' in df.columns:
        summary['sources'] = df['source'].value_counts().to_dict()
    
    return summary

def get_top_numbers(df: pd.DataFrame, top_n: int = 20) -> Dict[str, List[str]]:
    """
    Get top N most frequent phone numbers from caller and callee columns.
    """
    result = {
        'top_callers': [],
        'top_callees': [],
        'top_numbers': []
    }
    
    if df.empty:
        return result
    
    # Top callers
    if 'caller' in df.columns:
        top_callers = df['caller'].value_counts().head(top_n)
        result['top_callers'] = top_callers.index.tolist()
    
    # Top callees
    if 'callee' in df.columns:
        top_callees = df['callee'].value_counts().head(top_n)
        result['top_callees'] = top_callees.index.tolist()
    
    # Combined top numbers
    all_numbers = []
    if 'caller' in df.columns:
        all_numbers.extend(df['caller'].dropna().tolist())
    if 'callee' in df.columns:
        all_numbers.extend(df['callee'].dropna().tolist())
    
    if all_numbers:
        number_counts = pd.Series(all_numbers).value_counts().head(top_n)
        result['top_numbers'] = number_counts.index.tolist()
    
    return result
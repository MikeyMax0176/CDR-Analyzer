import pandas as pd
import numpy as np
from typing import Dict, List

def validate_cdr(df: pd.DataFrame) -> dict:
    errors: List[str] = []
    warnings: List[str] = []
    required = ['start_time', 'caller', 'callee']
    for col in required:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    # Check duration_sec
    if 'duration_sec' in df.columns:
        if (df['duration_sec'] < 0).any():
            errors.append("Column 'duration_sec' has negative values.")

    # Check start_time parseability and nulls
    if 'start_time' in df.columns:
        start_time = df['start_time']
        parsed = pd.to_datetime(start_time, errors='coerce')
        n_unparseable = parsed.isna().sum()
        if n_unparseable > 0:
            rate = n_unparseable / len(df)
            if rate > 0.05:
                warnings.append(f"More than 5% of 'start_time' values are unparseable ({rate:.1%}).")
        if parsed.isna().all():
            errors.append("All 'start_time' values are unparseable.")

    # Phone number checks (caller/callee)
    for col in ['caller', 'callee']:
        if col in df.columns:
            lens = df[col].astype(str).str.len()
            n_short = (lens < 7).sum()
            n_long = (lens > 16).sum()
            if n_short > 0:
                warnings.append(f"{n_short} values in '{col}' are shorter than 7 digits.")
            if n_long > 0:
                warnings.append(f"{n_long} values in '{col}' are longer than 16 digits.")

    # IP address checks (ip_src, ip_dst)
    import ipaddress
    for col in ['ip_src', 'ip_dst']:
        if col in df.columns:
            def is_valid_ip(val):
                try:
                    ipaddress.ip_address(str(val))
                    return True
                except Exception:
                    return False
            n_invalid = (~df[col].astype(str).apply(is_valid_ip)).sum()
            if n_invalid > 0:
                warnings.append(f"{n_invalid} values in '{col}' are not valid IP addresses.")

    # MCC/MNC/LAC/TAC_LTE/ECI checks (lenient: warn if non-digit)
    for col in ['MCC', 'MNC', 'LAC', 'TAC_LTE', 'ECI']:
        if col in df.columns:
            n_nondigit = (~df[col].astype(str).str.isdigit()).sum()
            if n_nondigit > 0:
                warnings.append(f"{n_nondigit} values in '{col}' are not all digits.")

    # Summary DataFrame: dtype and null_rate
    summary = pd.DataFrame({
        'dtype': df.dtypes.astype(str),
        'null_rate': df.isnull().mean()
    })

    return {"errors": errors, "warnings": warnings, "summary": summary}

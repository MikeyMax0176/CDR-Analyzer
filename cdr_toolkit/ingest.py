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
    if 'start_time' in df.columns:
        try:
            pd.to_datetime(df['start_time'])
        except Exception:
            errors.append("Column 'start_time' contains unparseable values.")
    if 'duration_sec' in df.columns:
        if (df['duration_sec'] < 0).any():
            errors.append("Column 'duration_sec' has negative values.")
    for col in ['caller', 'callee']:
        if col in df.columns:
            bad_phones = df[col].astype(str).str.match(r'^[0-9]{10,15}$') == False
            if bad_phones.any():
                warnings.append(f"Column '{col}' has values that do not look like phone numbers (10-15 digits).")
    null_perc = df.isnull().mean().to_dict()
    for col, perc in null_perc.items():
        if perc > 0.5:
            warnings.append(f"Column '{col}' has more than 50% missing values.")
    summary = df.describe(include='all').to_dict()
    return {"errors": errors, "warnings": warnings, "summary": summary, "nulls": null_perc}

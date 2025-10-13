import re
import pandas as pd

# List of identifier columns that should be treated as strings
ID_COLS = ["caller", "callee", "imei", "imsi", "cell_id", "lac", "call_id"]


def clean_identifier_series(s):
    """
    Clean identifier series by stripping non-digits and ensuring string dtype
    """
    if s.empty:
        return s.astype(str)

    # Convert to string first
    clean_s = s.astype(str)

    # Strip non-digit characters and clean up
    clean_s = clean_s.str.replace(r"[^\d]", "", regex=True)

    # Replace empty strings with NaN
    clean_s = clean_s.replace("", pd.NA)

    # Ensure it stays as string dtype
    return clean_s.astype("string")


def normalize_identifiers(df):
    """
    Normalize identifier columns to ensure proper string formatting
    """
    df_copy = df.copy()

    for col in ID_COLS:
        if col in df_copy.columns:
            df_copy[col] = clean_identifier_series(df_copy[col])

    return df_copy


def normalize_msisdn(x):
    if pd.isnull(x) or str(x).strip() == "":
        return None
    digits = re.sub(r"\D", "", str(x))
    if len(digits) == 10:
        digits = "1" + digits
    return digits if digits else None


def read_any(up):
    import pandas as pd
    import io

    name = getattr(up, "name", "")
    ext = name.split(".")[-1].lower() if "." in name else ""
    up.seek(0)
    if ext == "tsv":
        return pd.read_csv(up, sep="\t", low_memory=False)
    else:
        return pd.read_csv(up, sep=",", low_memory=False)


def coerce_types(df, mapping):
    # mapping: {canonical: source_col}
    import pandas as pd
    import numpy as np

    if not mapping:
        return df.copy()

    # Only keep columns in mapping values that exist in df
    mapping = {k: v for k, v in mapping.items() if v in df.columns}
    canon = df.rename(columns={v: k for k, v in mapping.items()})

    # Keep originals if present
    for col in ["caller", "callee"]:
        src = mapping.get(col)
        if src and src in df.columns:
            canon[f"{col}_raw"] = df[src]

    # Apply specific type coercion for each field type

    # 1. Phone numbers (caller, callee) - normalize and keep as strings
    for col in ["caller", "callee"]:
        if col in canon.columns:
            canon[col] = canon[col].apply(normalize_msisdn)

    # 2. IMEI and IMSI - keep as strings, preserve leading zeros
    for col in ["imei", "imsi"]:
        if col in canon.columns:
            # Convert to string and clean, but preserve leading zeros
            canon[col] = canon[col].astype(str).str.strip()
            # Replace 'nan', 'NaN', 'None' with actual NaN
            canon[col] = canon[col].replace(["nan", "NaN", "None", ""], np.nan)
            # For IMEI, ensure it's 15 digits (pad with leading zeros if needed)
            if col == "imei":
                # Only pad if it looks like a valid IMEI (all digits, reasonable length)
                def clean_imei(val):
                    if pd.isna(val) or val == "":
                        return np.nan
                    clean_val = str(val).strip()
                    # Remove any non-digit characters
                    digits_only = "".join(c for c in clean_val if c.isdigit())
                    # If it's 14 digits, pad with leading zero (common issue)
                    if len(digits_only) == 14:
                        return "0" + digits_only
                    # If it's 15 digits, return as-is
                    elif len(digits_only) == 15:
                        return digits_only
                    # Otherwise return the original cleaned value
                    else:
                        return clean_val if clean_val else np.nan

                canon[col] = canon[col].apply(clean_imei)

            # For IMSI, typically 15 digits but can vary by country
            elif col == "imsi":

                def clean_imsi(val):
                    if pd.isna(val) or val == "":
                        return np.nan
                    clean_val = str(val).strip()
                    # Remove any non-digit characters for IMSI
                    digits_only = "".join(c for c in clean_val if c.isdigit())
                    return digits_only if digits_only else clean_val if clean_val else np.nan

                canon[col] = canon[col].apply(clean_imsi)

    # 3. Timestamps - parse to datetime
    for col in ["start_time", "end_time"]:
        if col in canon.columns:
            canon[col] = pd.to_datetime(canon[col], errors="coerce")

    # 4. Duration - convert to numeric (seconds)
    if "duration" in canon.columns:
        canon["duration"] = pd.to_numeric(canon["duration"], errors="coerce")

    # 5. Cell ID, LAC - keep as strings to preserve leading zeros
    for col in ["cell_id", "lac"]:
        if col in canon.columns:
            canon[col] = canon[col].astype(str).str.strip()
            canon[col] = canon[col].replace(["nan", "NaN", "None", ""], np.nan)

    # 6. Coordinates - convert to numeric
    for col in ["latitude", "longitude"]:
        if col in canon.columns:
            canon[col] = pd.to_numeric(canon[col], errors="coerce")

    # 7. Call type, direction, technology - keep as categorical strings
    for col in ["call_type", "direction", "technology"]:
        if col in canon.columns:
            canon[col] = canon[col].astype(str).str.strip().str.lower()
            canon[col] = canon[col].replace(["nan", "none", ""], np.nan)

    # Reorder columns to canonical order if possible
    ordered_cols = [k for k in mapping.keys() if k in canon.columns]
    raw_cols = [c for c in canon.columns if c.endswith("_raw")]
    canon = canon[ordered_cols + raw_cols]

    # Normalize identifier columns to ensure proper string formatting
    canon = normalize_identifiers(canon)

    return canon


import pandas as pd
import numpy as np
from typing import Dict, List


def validate_cdr(df: pd.DataFrame) -> dict:
    errors: List[str] = []
    warnings: List[str] = []
    required = ["start_time", "caller", "callee"]
    for col in required:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    # Check duration_sec
    if "duration_sec" in df.columns:
        if (df["duration_sec"] < 0).any():
            errors.append("Column 'duration_sec' has negative values.")

    # Check start_time parseability and nulls
    if "start_time" in df.columns:
        start_time = df["start_time"]
        parsed = pd.to_datetime(start_time, errors="coerce")
        n_unparseable = parsed.isna().sum()
        if n_unparseable > 0:
            rate = n_unparseable / len(df)
            if rate > 0.05:
                warnings.append(
                    f"More than 5% of 'start_time' values are unparseable ({rate:.1%})."
                )
        if parsed.isna().all():
            errors.append("All 'start_time' values are unparseable.")

    # Phone number checks (caller/callee)
    for col in ["caller", "callee"]:
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

    for col in ["ip_src", "ip_dst"]:
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

    # IMEI validation (should be 15 digits)
    if "imei" in df.columns:
        imei_series = df["imei"].dropna().astype(str)
        if len(imei_series) > 0:
            # Check for proper IMEI format (15 digits)
            valid_imei = imei_series.str.match(r"^\d{15}$")
            n_invalid_imei = (~valid_imei).sum()
            if n_invalid_imei > 0:
                warnings.append(
                    f"{n_invalid_imei} IMEI values are not in standard 15-digit format."
                )

            # Check for obviously invalid IMEIs (all zeros, all same digit)
            all_zeros = (imei_series == "000000000000000").sum()
            all_same = imei_series.apply(
                lambda x: len(set(x)) == 1 if len(x) == 15 else False
            ).sum()
            if all_zeros > 0:
                warnings.append(f"{all_zeros} IMEI values are all zeros (likely invalid).")
            if all_same > 0:
                warnings.append(
                    f"{all_same} IMEI values have all identical digits (likely invalid)."
                )

    # IMSI validation (typically 15 digits, but can be 14-15)
    if "imsi" in df.columns:
        imsi_series = df["imsi"].dropna().astype(str)
        if len(imsi_series) > 0:
            # Check for proper IMSI format (14-15 digits)
            valid_imsi = imsi_series.str.match(r"^\d{14,15}$")
            n_invalid_imsi = (~valid_imsi).sum()
            if n_invalid_imsi > 0:
                warnings.append(
                    f"{n_invalid_imsi} IMSI values are not in standard 14-15 digit format."
                )

            # Check for obviously invalid IMSIs
            all_zeros = (imsi_series.str.match(r"^0+$")).sum()
            if all_zeros > 0:
                warnings.append(f"{all_zeros} IMSI values are all zeros (likely invalid).")

    # MCC/MNC/LAC/TAC_LTE/ECI checks (lenient: warn if non-digit)
    for col in ["MCC", "MNC", "LAC", "TAC_LTE", "ECI"]:
        if col in df.columns:
            n_nondigit = (~df[col].astype(str).str.isdigit()).sum()
            if n_nondigit > 0:
                warnings.append(f"{n_nondigit} values in '{col}' are not all digits.")

    # Summary DataFrame: dtype and null_rate
    summary = pd.DataFrame({"dtype": df.dtypes.astype(str), "null_rate": df.isnull().mean()})

    return {"errors": errors, "warnings": warnings, "summary": summary}

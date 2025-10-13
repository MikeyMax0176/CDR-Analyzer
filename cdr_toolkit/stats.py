import pandas as pd
from collections import Counter


def kpis(df):
    records = len(df)
    calls = df[df.get("type", "").eq("call")].shape[0] if "type" in df else records
    sms = df[df.get("type", "").eq("sms")].shape[0] if "type" in df else 0
    unique_numbers = (
        pd.unique(df[["caller", "callee"]].values.ravel("K")).size
        if "caller" in df and "callee" in df
        else 0
    )
    top_caller = df["caller"].mode()[0] if "caller" in df and not df["caller"].empty else None
    return dict(
        records=records, calls=calls, sms=sms, unique_numbers=unique_numbers, top_caller=top_caller
    )


def top_callers(df, n=20):
    if "caller" not in df:
        return pd.DataFrame()
    return (
        df["caller"]
        .value_counts()
        .head(n)
        .reset_index()
        .rename(columns={"index": "caller", "caller": "count"})
    )


def top_pairs(df, n=20):
    if "caller" not in df or "callee" not in df:
        return pd.DataFrame()
    pairs = df[["caller", "callee"]].apply(
        lambda row: tuple(sorted([str(row["caller"]), str(row["callee"])])), axis=1
    )
    pair_counts = Counter(pairs)
    top = pair_counts.most_common(n)
    return pd.DataFrame(top, columns=["pair", "count"]).assign(
        caller=lambda d: d["pair"].apply(lambda x: x[0]),
        callee=lambda d: d["pair"].apply(lambda x: x[1]),
    )[["caller", "callee", "count"]]


def daily_volume(df):
    if "start_time" not in df:
        return pd.Series(dtype=int)
    dt = pd.to_datetime(df["start_time"], errors="coerce")
    return dt.dt.date.value_counts().sort_index()


def hourly_volume(df):
    if "start_time" not in df:
        return pd.Series(dtype=int)
    dt = pd.to_datetime(df["start_time"], errors="coerce")
    return dt.dt.hour.value_counts().sort_index()


def top_contacts_for(df, number, n=20):
    if "caller" not in df or "callee" not in df:
        return pd.DataFrame()
    mask = (df["caller"] == number) | (df["callee"] == number)
    contacts = df[mask].apply(
        lambda row: row["callee"] if row["caller"] == number else row["caller"], axis=1
    )
    return (
        contacts.value_counts()
        .head(n)
        .reset_index()
        .rename(columns={"index": "contact", "callee": "count"})
    )

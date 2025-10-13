import streamlit as st
import pandas as pd
from cdr_toolkit.stats import (
    kpis,
    top_callers,
    top_pairs,
    daily_volume,
    hourly_volume,
    top_contacts_for,
)
import io
import plotly.express as px

st.header("Stats & Visuals")

# Prefer active_df if available, otherwise use dataset selection
if "active_df" in st.session_state and not st.session_state["active_df"].empty:
    df = st.session_state["active_df"]
    st.success(
        f"📊 Using combined filtered dataset ({len(df):,} rows from {df['source'].nunique() if 'source' in df.columns else 1} source(s))"
    )

    # Show source distribution if multiple sources
    if "source" in df.columns and df["source"].nunique() > 1:
        source_counts = df["source"].value_counts()
        st.markdown("**Data Sources:**")
        for source, count in source_counts.items():
            color = st.session_state.get("filters", {}).get("colors", {}).get(source, "#1f77b4")
            st.markdown(
                f"<span style='color: {color}'>●</span> {source}: {count:,} records",
                unsafe_allow_html=True,
            )
else:
    datasets = st.session_state.get("datasets", {})
    if not datasets:
        st.info("No datasets loaded in session. Please ingest data first.")
        st.stop()

    dataset_name = st.selectbox("Select dataset", list(datasets.keys()))
    df = datasets[dataset_name]
    st.info(
        "💡 Tip: Use 'Datasets & Filters' page to create a combined filtered dataset for enhanced analysis."
    )

# KPIs
metrics = kpis(df)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Records", metrics["records"])
col2.metric("Calls", metrics["calls"])
col3.metric("SMS", metrics["sms"])
col4.metric("Unique Numbers", metrics["unique_numbers"])
col5.metric("Top Caller", metrics["top_caller"] or "-")


# Top Callers
callers_df = top_callers(df)
st.subheader("Top Callers")
if not callers_df.empty and "caller" in callers_df.columns and "count" in callers_df.columns:
    callers_df["caller"] = callers_df["caller"].astype(str)
    st.bar_chart(callers_df.set_index("caller")["count"])
else:
    st.info("No 'caller' column found in this dataset.")
st.download_button("Download Top Callers CSV", callers_df.to_csv(index=False), "top_callers.csv")


pairs_df = top_pairs(df)
# --- Top Pairs Explorer ---
st.subheader("Top Pairs Explorer")
if not pairs_df.empty and {"caller", "callee", "count"}.issubset(pairs_df.columns):
    pairs_df["caller"] = pairs_df["caller"].astype(str)
    pairs_df["callee"] = pairs_df["callee"].astype(str)
    tab_bar, tab_heatmap, tab_sankey, tab_split, tab_drill = st.tabs(
        [
            "Bar (Undirected)",
            "Heatmap (Altair)",
            "Sankey (Plotly)",
            "Directional split",
            "Pair drill-down",
        ]
    )

    # Bar (Undirected)
    with tab_bar:
        undirected = pairs_df.copy()
        undirected["min"] = undirected[["caller", "callee"]].min(axis=1)
        undirected["max"] = undirected[["caller", "callee"]].max(axis=1)
        undirected["pair"] = undirected["min"] + " ↔ " + undirected["max"]
        bar_df = (
            undirected.groupby("pair", as_index=False)["count"]
            .sum()
            .sort_values("count", ascending=False)
            .head(20)
        )
        bar_df = bar_df.set_index("pair")
        st.bar_chart(bar_df)

    # Heatmap (Altair)
    with tab_heatmap:
        try:
            import altair as alt

            heat_df = pairs_df.copy().sort_values("count", ascending=False).head(200)
            chart = (
                alt.Chart(heat_df)
                .mark_rect()
                .encode(
                    x=alt.X("caller:N", sort=None),
                    y=alt.Y("callee:N", sort=None),
                    color=alt.Color("count:Q", scale=alt.Scale(scheme="blues")),
                    tooltip=["caller", "callee", "count"],
                )
                .properties(width=500, height=500)
            )
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.info(f"Altair not available or error: {e}")

    # Sankey (Plotly)
    with tab_sankey:
        try:
            import plotly.graph_objects as go

            sankey_df = pairs_df.copy().sort_values("count", ascending=False).head(50)
            nodes = (
                pd.Index(sankey_df["caller"])
                .append(pd.Index(sankey_df["callee"]))
                .unique()
                .tolist()
            )
            node_idx = {n: i for i, n in enumerate(nodes)}

            st.markdown("**Sankey Color & Contrast Options**")
            # Contrast sliders (0=black, 255=white)
            node_contrast = st.slider(
                "Node color contrast (0=black, 255=white)", 0, 255, 176, key="sankey_node_contrast"
            )
            link_contrast = st.slider(
                "Link color contrast (0=black, 255=white)", 0, 255, 144, key="sankey_link_contrast"
            )
            # Always use dark font for best contrast
            label_color = "#111111"
            # Node and link color as grayscale
            node_bg_color = f"#{node_contrast:02x}{node_contrast:02x}{node_contrast:02x}"
            link_color = f"#{link_contrast:02x}{link_contrast:02x}{link_contrast:02x}"
            node_colors = [node_bg_color] * len(nodes)
            link_colors = [link_color] * len(sankey_df)

            fig = go.Figure(
                go.Sankey(
                    node=dict(
                        label=nodes,
                        color=node_colors,
                        pad=10,
                        thickness=12,
                        line=dict(color=label_color, width=0.5),
                    ),
                    link=dict(
                        source=[node_idx[c] for c in sankey_df["caller"]],
                        target=[node_idx[c] for c in sankey_df["callee"]],
                        value=sankey_df["count"],
                        color=link_colors,
                    ),
                )
            )
            fig.update_layout(
                font=dict(color=label_color, size=13),
                plot_bgcolor="#f8f9fa",
                paper_bgcolor="#f8f9fa",
                margin=dict(l=10, r=10, t=30, b=10),
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.info(f"Plotly not available or error: {e}")

    # Directional split
    with tab_split:
        outbound = (
            pairs_df.groupby("caller", as_index=False)["count"]
            .sum()
            .sort_values("count", ascending=False)
            .head(15)
        )
        inbound = (
            pairs_df.groupby("callee", as_index=False)["count"]
            .sum()
            .sort_values("count", ascending=False)
            .head(15)
        )
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(outbound.set_index("caller")["count"])
            st.caption("Top 15 Outbound Callers")
        with col2:
            st.bar_chart(inbound.set_index("callee")["count"])
            st.caption("Top 15 Inbound Callees")

    # Pair drill-down
    with tab_drill:
        a = st.text_input("Party A (number)")
        b = st.text_input("Party B (number)")
        if a and b:
            drill = df[
                ((df["caller"].astype(str) == a) & (df["callee"].astype(str) == b))
                | ((df["caller"].astype(str) == b) & (df["callee"].astype(str) == a))
            ]
            st.dataframe(drill)
            if "start_time" in drill:
                dt = pd.to_datetime(drill["start_time"], errors="coerce")
                per_day = dt.dt.date.value_counts().sort_index()
                st.line_chart(per_day)
else:
    st.info("No caller/callee columns found in this dataset.")
st.download_button("Download Top Pairs CSV", pairs_df.to_csv(index=False), "top_pairs.csv")

# Daily Volume
st.subheader("Daily Volume")
daily = daily_volume(df)

# Add source-based coloring if multiple sources
if "source" in df.columns and df["source"].nunique() > 1:
    # Group by source and date for colored time series
    try:
        # Ensure we have timestamp column
        timestamp_cols = ["start_time", "ts", "timestamp", "datetime"]
        ts_col = None
        for col in timestamp_cols:
            if col in df.columns:
                ts_col = col
                break

        if ts_col:
            df_ts = df.copy()
            df_ts["date"] = pd.to_datetime(df_ts[ts_col], errors="coerce").dt.date

            # Group by source and date
            source_daily = df_ts.groupby(["source", "date"]).size().reset_index()
            source_daily.columns = ["source", "date", "count"]
            source_daily["date"] = pd.to_datetime(source_daily["date"])

            # Use stored colors
            color_map = st.session_state.get("filters", {}).get("colors", {})

            fig = px.line(
                source_daily,
                x="date",
                y="count",
                color="source",
                title="Daily Volume by Source",
                color_discrete_map=color_map,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(daily)
    except Exception as e:
        st.line_chart(daily)
        st.caption(f"Source coloring failed: {e}")
else:
    st.line_chart(daily)

st.download_button("Download Daily Volume CSV", daily.to_csv(), "daily_volume.csv")

# Hourly Volume
st.subheader("Hourly Volume")
hourly = hourly_volume(df)

# Add source-based coloring if multiple sources
if "source" in df.columns and df["source"].nunique() > 1:
    try:
        # Ensure we have timestamp column
        timestamp_cols = ["start_time", "ts", "timestamp", "datetime"]
        ts_col = None
        for col in timestamp_cols:
            if col in df.columns:
                ts_col = col
                break

        if ts_col:
            df_ts = df.copy()
            df_ts["hour"] = pd.to_datetime(df_ts[ts_col], errors="coerce").dt.hour

            # Group by source and hour
            source_hourly = df_ts.groupby(["source", "hour"]).size().reset_index()
            source_hourly.columns = ["source", "hour", "count"]

            # Use stored colors
            color_map = st.session_state.get("filters", {}).get("colors", {})

            fig = px.bar(
                source_hourly,
                x="hour",
                y="count",
                color="source",
                title="Hourly Volume by Source",
                color_discrete_map=color_map,
                barmode="stack",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(hourly)
    except Exception as e:
        st.bar_chart(hourly)
        st.caption(f"Source coloring failed: {e}")
else:
    st.bar_chart(hourly)

st.download_button("Download Hourly Volume CSV", hourly.to_csv(), "hourly_volume.csv")

# Top Contacts for a Number
st.subheader("Top Contacts for a Number")
target = st.text_input("Target number")
if target:
    contacts_df = top_contacts_for(df, target)
    st.dataframe(contacts_df)
    st.download_button(
        "Download Top Contacts CSV", contacts_df.to_csv(index=False), "top_contacts.csv"
    )
    # Per-day line chart for that number
    mask = (df["caller"] == target) | (df["callee"] == target)
    if "start_time" in df:
        dt = pd.to_datetime(df.loc[mask, "start_time"], errors="coerce")
        per_day = dt.dt.date.value_counts().sort_index()
        st.line_chart(per_day)

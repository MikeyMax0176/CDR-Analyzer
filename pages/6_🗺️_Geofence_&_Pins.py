import streamlit as st
import pandas as pd
from cdr_toolkit import towers

st.title("🗺️ Geofence & Pins")
from cdr_toolkit.ui import render_snapshot_button

render_snapshot_button()

# --- Upload/Update Towers CSV ---
st.header("Upload or Update Tower List")
tower_file = st.file_uploader(
    "Upload towers CSV (eci, enb, sector, lat, lon, azimuth, beamwidth)", type=["csv"]
)
if tower_file:
    df_towers = pd.read_csv(tower_file)
    towers.upsert_towers(df_towers)
    st.success(f"Uploaded {len(df_towers)} towers. Database updated.")

# --- Search/Filter Towers Table ---
st.header("Tower Table")
search = st.text_input("Search towers (ECI, ENB, sector)")
tower_df = towers.fetch_towers(search)
st.dataframe(tower_df, use_container_width=True)

# --- Apply to active_df ---
if "active_df" in st.session_state and not st.session_state["active_df"].empty:
    st.header("Map Tower Coordinates to Active Dataset")
    apply = st.checkbox("Apply tower lat/lon to active_df (by ECI/CGI)")
    if apply:
        df = st.session_state["active_df"]
        # Try to map ECI or CGI columns
        eci_col = None
        for col in ["eci", "cgi", "cell_id"]:
            if col in df.columns:
                eci_col = col
                break
        if eci_col:
            merged = df.merge(
                tower_df[["eci", "lat", "lon"]],
                left_on=eci_col,
                right_on="eci",
                how="left",
                suffixes=("", "_tower"),
            )
            st.session_state["active_df"] = merged
            st.success(f"Mapped tower coordinates to {merged['lat'].notna().sum()} records.")
        else:
            st.warning("No ECI/CGI/cell_id column found in active_df.")
else:
    st.info("No active dataset loaded. Use Datasets & Filters page to create one.")

# --- Map Calls with Pydeck ---
st.header("Map Calls (active_df)")
if "active_df" in st.session_state and not st.session_state["active_df"].empty:
    df = st.session_state["active_df"]
    if {"lat", "lon"}.issubset(df.columns):
        import pydeck as pdk

        st.subheader("Call Locations Map")
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df.dropna(subset=["lat", "lon"]),
            get_position="[lon, lat]",
            get_color="[200, 30, 0, 160]",
            get_radius=30,
            pickable=True,
        )
        view_state = pdk.ViewState(
            latitude=df["lat"].mean(), longitude=df["lon"].mean(), zoom=10, pitch=0
        )
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "Source: {source}\nLat: {lat}\nLon: {lon}"},
        )
        st.pydeck_chart(r)
    else:
        st.info("No lat/lon columns in active_df.")

    # --- Drawing Tools: Polygon (Geofence) and Pins ---
    st.subheader("Draw Geofence or Pins")
    import shapely.geometry
    import json

    # Store drawn shapes in session_state
    if "geo_drawings" not in st.session_state:
        st.session_state["geo_drawings"] = {"polygons": [], "pins": []}

    draw_type = st.radio("Draw:", ["Polygon (Geofence)", "Pin (Point)"])
    if draw_type == "Polygon (Geofence)":
        poly_coords = st.text_area(
            "Enter polygon coordinates as JSON (e.g. [[lon,lat],...])", key="poly_coords"
        )
        if st.button("Add Geofence Polygon") and poly_coords.strip():
            try:
                coords = json.loads(poly_coords)
                st.session_state["geo_drawings"]["polygons"].append(coords)
                st.success("Polygon added.")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
    else:
        pin_coords = st.text_input("Enter pin coordinates as 'lon,lat'", key="pin_coords")
        if st.button("Add Pin") and pin_coords.strip():
            try:
                lon, lat = map(float, pin_coords.split(","))
                st.session_state["geo_drawings"]["pins"].append([lon, lat])
                st.success("Pin added.")
            except Exception as e:
                st.error(f"Invalid coordinates: {e}")

    # Show current drawings
    st.markdown("**Current Geofences:**")
    for i, poly in enumerate(st.session_state["geo_drawings"]["polygons"]):
        st.json(poly)
    st.markdown("**Current Pins:**")
    for i, pin in enumerate(st.session_state["geo_drawings"]["pins"]):
        st.write(f"Pin {i+1}: {pin}")

    # --- Filter active_df by geofence polygon ---
    if st.session_state["geo_drawings"]["polygons"]:
        st.subheader("Filter Calls by Geofence")
        from shapely.geometry import Point, Polygon

        filtered = pd.DataFrame()
        for poly in st.session_state["geo_drawings"]["polygons"]:
            polygon = Polygon(poly)
            mask = df.apply(lambda row: polygon.contains(Point(row["lon"], row["lat"])), axis=1)
            filtered = pd.concat([filtered, df[mask]])
        filtered = filtered.drop_duplicates()
        st.write(f"Calls inside geofence: {len(filtered):,}")
        # Show call counts per source
        if "source" in filtered.columns:
            st.dataframe(
                filtered["source"]
                .value_counts()
                .reset_index()
                .rename(columns={"index": "Source", "source": "Call Count"})
            )
        else:
            st.write("No source column in filtered data.")
        # Optionally show filtered data
        st.dataframe(filtered.head(100))

    # --- Add Note tied to selected pin or geofence ---
    from cdr_toolkit.notes import render_notes

    st.subheader("Add Note to Geofence or Pin")
    geo_context = {}
    geo_type = st.radio(
        "Select to add note to:",
        ["None"]
        + [f"Geofence {i+1}" for i in range(len(st.session_state["geo_drawings"]["polygons"]))]
        + [f"Pin {i+1}" for i in range(len(st.session_state["geo_drawings"]["pins"]))],
        key="geo_note_select",
    )
    if geo_type != "None":
        if geo_type.startswith("Geofence"):
            idx = int(geo_type.split()[1]) - 1
            geo_context = {
                "type": "polygon",
                "coords": st.session_state["geo_drawings"]["polygons"][idx],
            }
        elif geo_type.startswith("Pin"):
            idx = int(geo_type.split()[1]) - 1
            geo_context = {"type": "pin", "coords": st.session_state["geo_drawings"]["pins"][idx]}
    # Use case_id=None for now (or set if available)
    render_notes(case_id=None, page="Geofence & Pins", context={"geo": geo_context})

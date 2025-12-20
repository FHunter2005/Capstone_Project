# Project/map_tab.py
import re
import folium
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium

from services.db_service import DatabaseService

_COORD_AT = re.compile(r"@([-0-9.]+),([-0-9.]+)")
_COORD_LOC = re.compile(r"loc:([-0-9.]+)\+([-0-9.]+)")

def _coords_from_google_maps(url: str):
    if not url or not isinstance(url, str) or not url.strip():
        return None

    m = _COORD_AT.search(url)
    if m:
        return float(m.group(1)), float(m.group(2))

    m = _COORD_LOC.search(url)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None

@st.cache_data(ttl=3600)
def _load_maps_df():
    db = DatabaseService()
    docs = list(db.maps_location().find({}, {"Institution": 1, "GoogleMaps": 1, "_id": 0}))
    return pd.DataFrame(docs)

def render_university_map():
    st.subheader("Interactive City Map")

    try:
        df_maps = _load_maps_df()
    except Exception as e:
        st.error(f"MongoDB error loading map data: {e}")
        st.stop()

    if df_maps.empty:
        st.warning("No locations found in Maps_Location collection.")
        st.stop()

    university = dict(zip(df_maps["Institution"], df_maps["GoogleMaps"]))

    selected_university = st.selectbox("Select a University", list(university.keys()))
    url = university.get(selected_university, "")

    coords = _coords_from_google_maps(url)
    if coords is None:
        st.error(f"Could not extract coordinates from Google Maps link for: {selected_university}")
        st.stop()

    lat, lon = coords

    m = folium.Map(location=[lat, lon], zoom_start=14)
    folium.Marker(
        location=[lat, lon],
        popup=selected_university,
        tooltip=selected_university,
        icon=folium.Icon(color="red"),
    ).add_to(m)

    st_folium(m, width=1200, height=500)

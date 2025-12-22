# Project/map_tab.py
import re
import folium
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium

from services.db_service import DatabaseService

"""
Map Visualization Module.

This module is responsible for rendering the interactive university map in the Streamlit UI.
It fetches geospatial data (Google Maps links) from the database, extracts raw coordinates
using Regex, and plots them using Leaflet.js (via Folium).
"""

# Regex patterns to extract latitude/longitude from Google Maps URLs.
# Pattern 1: Standard URL (e.g., ...@38.71667,-9.13333...)
_COORD_AT = re.compile(r"@([-0-9.]+),([-0-9.]+)")
# Pattern 2: Search/Directions URL (e.g., ...loc:38.71667+-9.13333...)
_COORD_LOC = re.compile(r"loc:([-0-9.]+)\+([-0-9.]+)")

def _coords_from_google_maps(url: str):
    """
    Parses a Google Maps URL to extract the latitude and longitude.

    It supports multiple URL formats commonly used by Google Maps (Share links, search results).
    
    Args:
        url (str): The Google Maps URL string.

    Returns:
        tuple[float, float] | None: A tuple of (latitude, longitude) if found, else None.
    """
    if not url or not isinstance(url, str) or not url.strip():
        return None

    # Try matching the standard '@lat,lon' format first
    m = _COORD_AT.search(url)
    if m:
        return float(m.group(1)), float(m.group(2))

    # Fallback to the 'loc:lat+lon' format used in some share links
    m = _COORD_LOC.search(url)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None

@st.cache_data(ttl=3600)
def _load_maps_df():
    """
    Fetches University Location data from MongoDB.

    Optimization:
    - Uses @st.cache_data with a 1-hour TTL (Time To Live).
    - This prevents hitting the database on every UI interaction (zoom/pan), 
      significantly improving map rendering performance.
    
    Returns:
        pd.DataFrame: A DataFrame containing 'Institution' names and 'GoogleMaps' URLs.
    """
    db = DatabaseService()
    # Fetch only necessary fields to minimize data transfer overhead
    docs = list(db.maps_location().find({}, {"Institution": 1, "GoogleMaps": 1, "_id": 0}))
    return pd.DataFrame(docs)

def render_university_map():
    """
    Renders the Interactive Map Component.

    Workflow:
    1. Loads map data (cached).
    2. Displays a dropdown for the user to select a university.
    3. Extracts coordinates from the selected university's URL.
    4. Plots the marker on a Folium map and renders it in Streamlit.
    """
    st.subheader("Interactive City Map")

    try:
        df_maps = _load_maps_df()
    except Exception as e:
        st.error(f"MongoDB error loading map data: {e}")
        st.stop()

    if df_maps.empty:
        st.warning("No locations found in Maps_Location collection.")
        st.stop()

    # Create a lookup dictionary: Institution Name -> Map URL
    university = dict(zip(df_maps["Institution"], df_maps["GoogleMaps"]))

    selected_university = st.selectbox("Select a University", list(university.keys()))
    url = university.get(selected_university, "")

    # Convert the stored URL into plot-able coordinates
    coords = _coords_from_google_maps(url)
    if coords is None:
        st.error(f"Could not extract coordinates from Google Maps link for: {selected_university}")
        st.stop()

    lat, lon = coords

    # Initialize the Map centered on the target university
    m = folium.Map(location=[lat, lon], zoom_start=14)
    
    # Add a visual marker with a popup
    folium.Marker(
        location=[lat, lon],
        popup=selected_university,
        tooltip=selected_university,
        icon=folium.Icon(color="red"),
    ).add_to(m)

    # Render the map within the Streamlit layout
    st_folium(m, width=1200, height=500)
import re
import folium
import streamlit as st
import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from streamlit_folium import st_folium   # <-- Correct import

# ---------- Load env ----------
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
maps_collection = db.Maps_Location

if not MONGO_URI or not MONGO_DB:
    raise RuntimeError("Missing MONGO_URI or MONGO_DB in .env")

def render_university_map():
    # Load universities from MongoDB
    df_maps = pd.DataFrame(list(maps_collection.find()))
    university = dict(zip(df_maps["Institution"], df_maps["GoogleMaps"]))

    st.subheader("Interactive City Map")

    # Select a university
    selected_university = st.selectbox("Select a University", list(university.keys()))
    url = university[selected_university]

    # Extract coordinates
    def coords_from_google_maps(url):
        if pd.isna(url) or url.strip() == "":
            return None
        
        match_at = re.search(r'@([-0-9.]+),([-0-9.]+)', url)
        if match_at:
            return float(match_at.group(1)), float(match_at.group(2))

        match_loc = re.search(r'loc:([-0-9.]+)\+([-0-9.]+)', url)
        if match_loc:
            return float(match_loc.group(1)), float(match_loc.group(2))

        return None

    coords = coords_from_google_maps(url)

    if coords is None:
        st.error(f"⚠️ Could not extract coordinates from Google Maps link for: {selected_university}")
        return

    lat, lon = coords

    # ---------------------------
    #        FOLIUM MAP
    # ---------------------------

    m = folium.Map(location=[lat, lon], zoom_start=14)

    # Marker with popup
    folium.Marker(
        location=[lat, lon],
        popup=selected_university,
        tooltip=selected_university,
        icon=folium.Icon(color="red")
    ).add_to(m)

    # Render Folium map in Streamlit
    st_folium(m, width=1200, height=500)

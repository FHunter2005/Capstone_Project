# map_tab.py
import re
from soupsieve import match
import streamlit as st
import pandas as pd
import pydeck as pdk
from pymongo import MongoClient
import os
from dotenv import load_dotenv

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
    # Dictionary of universities with coordinates
    df_maps = pd.DataFrame(list(maps_collection.find()))  # CSV separado por ;
    university = dict(zip(df_maps["Institution"], df_maps["GoogleMaps"]))


    st.subheader("Interactive City Map")

    # University selector
    selected_university = st.selectbox("Select a University", list(university.keys()))
    url = university[selected_university]

    # Get coordinates
    def coords_from_google_maps(url):
        if pd.isna(url) or url.strip() == "":
            return None
        
        # Try standard @lat,lon first
        match_at = re.search(r'@([-0-9.]+),([-0-9.]+)', url)
        if match_at:
            return float(match_at.group(1)), float(match_at.group(2))
        
        # Try loc:lat+lon format
        match_loc = re.search(r'loc:([-0-9.]+)\+([-0-9.]+)', url)
        if match_loc:
            return float(match_loc.group(1)), float(match_loc.group(2))
        
        # If no match
        return None




    
    coords = coords_from_google_maps(url)

    # If no coordinates were found, avoid crash and inform the user
    if coords is None:
        st.error(f"⚠️ Could not extract coordinates from the Google Maps link for: {selected_university}")
        return  # Stop rendering the map
    
    # DataFrame for map
    df = pd.DataFrame({
        'lat': [coords[0]],
        'lon': [coords[1]],
        'name': [selected_university]
    })

    # Create PyDeck layer with smaller markers
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_color='[255, 0, 0, 160]',
        get_radius=50,
        pickable=True,
    )

    # Set view state
    view_state = pdk.ViewState(
        latitude=coords[0],
        longitude=coords[1],
        zoom=13.5,
        pitch=0,
    )

    # Render map
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{name}"}
        )
    )

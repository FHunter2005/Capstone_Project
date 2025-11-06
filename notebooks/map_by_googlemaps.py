import streamlit as st
import pandas as pd
import pydeck as pdk
import re

st.title("Interactive City Map (Google Maps Link Version)")

# Dictionary of universities with their Google Maps URLs
university = {
    "Nova IMS": "https://www.google.com/maps/place/NOVA+Information+Management+School/@38.7326765,-9.1599584,17z",
    "Nova FCSH": "https://www.google.com/maps/place/NOVA+FCSH/@38.7408181,-9.1507133,17z",
    "Nova FCT": "https://www.google.com/maps/place/NOVA+FCT/@38.6612614,-9.2053650,17z",
    "Universidade do Porto": "https://www.google.com/maps/place/Universidade+do+Porto/@41.1596861,-8.6250686,17z",
}

# University selector
selected_university = st.selectbox("Select a University", list(university.keys()))

# Get the Google Maps URL
url = university[selected_university]
st.write(f"🌍 Google Maps link: [Open in Maps]({url})")

# Function to extract coordinates from the Google Maps URL
def coords_from_google_maps(url):
    match = re.search(r'@([-0-9.]+),([-0-9.]+)', url)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None

# Extract coordinates
coords = coords_from_google_maps(url)

if coords:
    lat, lon = coords

    # Create DataFrame for map
    df = pd.DataFrame({
        'lat': [lat],
        'lon': [lon],
        'name': [selected_university]
    })

    # Create PyDeck layer
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_color='[255, 0, 0, 160]',
        get_radius=50,
        pickable=True,
    )

    # Define view state
    view_state = pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=13.5,
        pitch=0,
    )

    # Render map
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{name}"}))

else:
    st.error("❌ Could not extract coordinates from this Google Maps link.")

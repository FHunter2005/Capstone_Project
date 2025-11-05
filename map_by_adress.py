import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.geocoders import Nominatim

st.title("Interactive City Map (Address Version)")

# Dictionary of universities with their street addresses
university = {
    "Nova IMS": "Campus de Campolide, Lisboa, Portugal",
    "Nova FCSH": "Avenida de Berna 26-C, Lisboa, Portugal",
    "Nova FCT": "2829-516 Caparica, Portugal",
    "Universidade do Porto": "Praça de Gomes Teixeira, Porto, Portugal",
}

# University selector
selected_university = st.selectbox("Select a University", list(university.keys()))

# Get the address for the selected university
address = university[selected_university]

# Initialize geolocator
geolocator = Nominatim(user_agent="streamlit_map_app")

# Convert address to coordinates
location = geolocator.geocode(address)

if location:
    # Create a DataFrame with the coordinates
    df = pd.DataFrame({
        'lat': [location.latitude],
        'lon': [location.longitude],
        'name': [selected_university]
    })

    # Create PyDeck layer with smaller marker
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_color='[255, 0, 0, 160]',
        get_radius=50,
        pickable=True,
    )

    # Define map view
    view_state = pdk.ViewState(
        latitude=location.latitude,
        longitude=location.longitude,
        zoom=13.5,
        pitch=0,
    )

    # Render map
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{name}"}))

else:
    st.error(f"Could not find coordinates for: {address}")
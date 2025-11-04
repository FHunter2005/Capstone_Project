import streamlit as st
import pandas as pd
import pydeck as pdk

# Dictionary of universities with coordinates
university = {
    "Nova IMS": [38.73267651987515, -9.159958418944454],
    "Nova FCSH": [38.74081811181073, -9.15071327661429],
    "Nova FCT": [38.66126138110339, -9.205365003607264],
    "Universidade do Porto": [41.15968610535622, -8.625068575893907],
}

st.title("Interactive City Map")

# University selector
selected_university = st.selectbox("Select a University", list(university.keys()))

# Get coordinates
coords = university[selected_university]

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
    get_radius=50,  # smaller radius (adjust between 30–100)
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
st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{name}"}))
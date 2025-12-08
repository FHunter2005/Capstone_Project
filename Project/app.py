# app.py
# ===========================
# Masters Finder – Chatbot + Calculator
# ===========================
import base64
from pathlib import Path

import os
import streamlit as st

from calculator import render_price_calculator
from Project.map_tab import render_university_map
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "mm.jpg")
LOTTIE_PATH = os.path.join(BASE_DIR, "gif.json")
SIDE_PATH = os.path.join(BASE_DIR,"photo.jpg")

 # lottie animation JSON


# ---------- Page Config ----------
st.set_page_config(
    page_title="MasterMatch",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Session State ----------
def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "page" not in st.session_state:
        st.session_state.page = "chat"



init_state()

import json
import time
from streamlit_lottie import st_lottie

# ---------- Encode Assets ----------
def load_image_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ---------- Play Lottie Intro ----------
def play_lottie_intro(json_path: str, height: int = 300, width: int = 300, duration: int = 6):
    if st.session_state.get("intro_played", False):
        return
    st.session_state["intro_played"] = True

    try:
        with open(json_path, "r") as f:
            animation = json.load(f)
    except Exception as e:
        st.error(f"Could not load Lottie animation: {e}")
        return

    # Container for GIF
    container = st.empty()

    # CSS for rounded corners
    st.markdown(
        """
        <style>
        .stLottie iframe {
            border-radius: 20px !important;
            overflow: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with container:
        st_lottie(animation, height=height, key="intro_lottie")

    # Wait before showing main content
    time.sleep(duration)  # or your desired duration
    container.empty()  # removes intro GIF after duration




# ---------- Load Assets ----------
logo_base64 = load_image_base64(LOGO_PATH)
sidebar_bg_base64 = load_image_base64(SIDE_PATH)

# ---------- Show Lottie Intro ----------
play_lottie_intro(LOTTIE_PATH, height=300, width=300, duration=6)


st.markdown(
    f"""
    <style>
    /* Sidebar background image with dark overlay */
    [data-testid="stSidebar"] {{
        background-image:
            linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.95)),
            url("data:image/jpg;base64,{sidebar_bg_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}

    /* Style all sidebar buttons as pills */
    [data-testid="stSidebar"] .stButton > button {{
        background-color: rgba(0, 0, 0, 0.35) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 50px !important;
        padding: 14px 20px !important;
        font-size: 17px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        text-align: left !important;
        width: 100% !important;
        margin: 8px 0 !important;
    }}

    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: rgba(244, 180, 0, 0.25) !important;
        border-color: rgba(244, 180, 0, 0.6) !important;
        transform: translateX(5px) !important;
        box-shadow: 0 4px 12px rgba(244, 180, 0, 0.2) !important;
    }}

    /* "Active" look when focused (after click) */
    [data-testid="stSidebar"] .stButton > button:focus:not(:active) {{
        background-color: rgba(244, 180, 0, 0.3) !important;
        border-color: #F4B400 !important;
        box-shadow: 0 0 20px rgba(244, 180, 0, 0.4) !important;
        font-weight: 600 !important;
    }}

    /* Make sidebar content area transparent (no big card) */
    [data-testid="stSidebar"] > div:first-child {{
        background-color: transparent !important;
    }}

    /* Logo styling */
    [data-testid="stSidebar"] img.mm-logo {{
        width: 120px;
        border-radius: 16px;
        border: 3px solid #F4B400 !important;
        box-shadow: 0 4px 20px rgba(244,180,0,0.4) !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Header (Center) ----------
# Lottie animation on top

header_html = f"""
<div style="text-align: center; padding-top: 10px; padding-bottom: 10px;">
    <img src="data:image/png;base64,{logo_base64}"
         style="width:200px; border-radius:12px;"/>
    <h1 style="
        color: #F4B400;
        margin-top: 20px;
        font-weight: 700;
        font-size: 48px;
    ">MasterMatch</h1>
    <p style="
        font-size: 20px;
        color: lightgray;
        margin-top: -10px;
    ">Your personal AI advisor for master’s programs.</p>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)


# ---------- Sidebar Logo + Menu ----------
with st.sidebar:
    # Logo with glow + border
    st.markdown(
        f"""
        <div style="text-align: center; padding: 20px 0 30px;">
            <img src="data:image/png;base64,{logo_base64}"
                 class="mm-logo">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Navigation buttons
    if st.button("Chat", key="chat_btn", use_container_width=True):
        st.session_state.page = "chat"
        st.rerun()

    if st.button("Calculator", key="calc_btn", use_container_width=True):
        st.session_state.page = "calculator"
        st.rerun()

    if st.button("Map", key="map_btn", use_container_width=True):
        st.session_state.page = "map"
        st.rerun()


# ---------- Main Content ----------
selected = st.session_state.page

if selected == "chat":
    st.markdown("<br>", unsafe_allow_html=True)

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    prompt = st.chat_input(
        "Ask me about master's programs, tuition, rankings, or scholarships..."
    )
    if prompt:
        # User message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Assistant reply
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                api_url = "http://localhost:8000/query"
                payload = {"query": prompt}

                try:
                    api_response = requests.post(api_url, json=payload).json()
                    response = api_response.get("result", "❌ API returned no result.")
                except Exception as e:
                    response = f"❌ Error contacting backend API: {e}"
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

elif selected == "calculator":
    render_price_calculator()

elif selected == "map":
    st.markdown(
        "<h2 style='text-align: center; color: #F4B400;'>Top Universities Worldwide</h2>",
        unsafe_allow_html=True,
    )
    render_university_map()

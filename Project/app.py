# app.py
# ===========================
# Masters Finder – Chatbot + Calculator
# ===========================
import base64
import json
import os
import time
from pathlib import Path

import requests
import streamlit as st
from streamlit_lottie import st_lottie

# --- Custom Services ---
from services.auth_service import AuthService
from calculator import render_price_calculator
from Project.map_tab import render_university_map
from ai.ai_client import AIClient

# --- Constants & Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "mm.jpg")
LOTTIE_PATH = os.path.join(BASE_DIR, "gif.json")
SIDE_PATH = os.path.join(BASE_DIR, "photo.jpg")

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
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    if "last_recommended_masters" not in st.session_state:
        st.session_state.last_recommended_masters = []
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None

init_state()
auth_service = AuthService()

# ---------- Helper Functions ----------

def load_image_base64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def play_lottie_intro(json_path: str, height: int = 300, width: int = 300, duration: int = 6):
    if st.session_state.get("intro_played", False):
        return
    st.session_state["intro_played"] = True

    try:
        with open(json_path, "r") as f:
            animation = json.load(f)
    except Exception as e:
        return

    container = st.empty()
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

    time.sleep(duration)
    container.empty()


# ---------- Load Assets ----------
logo_base64 = load_image_base64(LOGO_PATH)
sidebar_bg_base64 = load_image_base64(SIDE_PATH)

# ---------- Show Lottie Intro ----------
play_lottie_intro(LOTTIE_PATH, height=300, width=300, duration=6)


# ---------- Custom CSS Styling ----------
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


# ---------- Authentication Flow ----------
if not st.session_state.logged_in:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #F4B400;'>Login MasterMatch</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Sign in", "Create Account"])
        
        # --- TAB LOGIN ---
        with tab1:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", use_container_width=True):
                user = auth_service.login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.messages = auth_service.load_history(username)
                    st.rerun()
                else:
                    st.error("Incorrect credentials.")

        # --- TAB SIGNUP ---
        with tab2:
            new_user = st.text_input("New Username", key="signup_user")
            new_name = st.text_input("Your Name", key="signup_name")
            new_pass = st.text_input("New Password", type="password", key="signup_pass")
            if st.button("Register", use_container_width=True):
                success, msg = auth_service.register_user(new_user, new_name, new_pass)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_info = {'username': new_user, 'name': new_name}
                    st.session_state.messages = []
                    st.success("Account created successfully! Logging in...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)

    st.stop()


# ---------- Main App Header ----------
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


# ---------- Sidebar Navigation ----------
with st.sidebar:
    st.markdown(
        f"""
        <div style="text-align: center; padding: 20px 0 30px;">
            <img src="data:image/png;base64,{logo_base64}"
                 class="mm-logo">
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("HISTORY")

    user_name = st.session_state.user_info['name']
    st.write(f"Hi, **{user_name}**! 👋")
    
    if st.button("Logout", key="logout_btn", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("<hr style='margin: 10px 0; border-color: #F4B400;'>", unsafe_allow_html=True)

    if st.button("Chat", key="chat_btn", use_container_width=True):
        st.session_state.page = "chat"
        st.rerun()

    if st.button("Calculator", key="calc_btn", use_container_width=True):
        st.session_state.page = "calculator"
        st.rerun()

    if st.button("Map", key="map_btn", use_container_width=True):
        st.session_state.page = "map"
        st.rerun()

    # --- Favorites Button ---
    if st.button("Favorites", key="fav_btn", use_container_width=True):
        st.session_state.page = "favorites"
        st.rerun()

    if st.button("➕ New Conversation", use_container_width=True):
        new_id = auth_service.create_new_thread(st.session_state.user_info['username'])

        st.session_state.current_thread_id = new_id
        st.session_state.messages = [] # Clear screen
        st.session_state.last_recommended_masters = []

        if "agent_client" in st.session_state:
            del st.session_state.agent_client
            
        st.rerun()
    
    threads = auth_service.get_user_threads(st.session_state.user_info['username'])
    
    for thread in threads:
        # If this is the active chat, make the button look "selected" (primary)
        b_type = "primary" if thread['id'] == st.session_state.current_thread_id else "secondary"
        
        # Button label: Title + Date
        label = f"{thread['title']} ({thread['date']})"
        
        if st.button(label, key=thread['id'], type=b_type, use_container_width=True):
            # Switch to this thread
            st.session_state.current_thread_id = thread['id']
            st.session_state.messages = auth_service.load_thread_messages(thread['id'])
            
            # Reset AI Memory (so it learns the NEW context)
            if "agent_client" in st.session_state:
                del st.session_state.agent_client
                
            st.rerun()
# ---------- Content Routing ----------
selected = st.session_state.page

if selected == "chat":
    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.current_thread_id is None:
        new_id = auth_service.create_new_thread(st.session_state.user_info['username'])
        st.session_state.current_thread_id = new_id

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    prompt = st.chat_input(
        "Ask me about master's programs, tuition, rankings, or scholarships..."
    )
    if prompt:
        st.session_state.last_recommended_masters = []

        # 1. Display User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        auth_service.save_message(st.session_state.current_thread_id, "user", prompt)

        if len(st.session_state.messages) == 1:
            # Simple title: first 30 chars of prompt
            new_title = prompt[:30] + "..." if len(prompt) > 30 else prompt
            auth_service.update_thread_title(st.session_state.current_thread_id, new_title)

        # 2. Generate Assistant Reply
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    if "agent_client" not in st.session_state:
                        past_history = st.session_state.messages[-20:]
                        st.session_state.agent_client = AIClient(history_messages=past_history)
                    
                    # LLM decides if it needs to search. If it does, 
                    # agent_tools.py will populate 'last_recommended_masters'
                    response = st.session_state.agent_client.send_message_to_agent(prompt)
                    
                except Exception as e:
                    response = f"❌ Error: {e}"
            
            st.markdown(response)

        # 3. Save Assistant Message
        st.session_state.messages.append({"role": "assistant", "content": response})
        auth_service.save_message(st.session_state.current_thread_id, "assistant", response)

    if st.session_state.last_recommended_masters:
        st.markdown("---")
        st.caption("👇 **Found Programs (Click 'Save' to add to Favorites)**")
        
        for prog in st.session_state.last_recommended_masters:
            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{prog.get('master', 'Unknown')}** at *{prog.get('university', 'Unknown')}*")
                with c2:
                    unique_id = str(prog.get('_id'))
                    btn_key = f"save_{unique_id}"
                    
                    if st.button("❤️ Save", key=btn_key):
                        # Verify we have the user info
                        if st.session_state.user_info:
                            success, msg = auth_service.add_favorite(
                                st.session_state.user_info['username'], 
                                prog
                            )
                            if success:
                                st.toast(f"Saved: {prog.get('master')}", icon="✅")
                            else:
                                st.toast(msg, icon="ℹ️")
                        else:
                            st.error("You must be logged in to save.")

elif selected == "favorites":
    st.markdown("<h2 style='text-align: center; color: #F4B400;'>My Favorite Programs ❤️</h2>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    favs = auth_service.get_user_favorites(st.session_state.user_info['username'])
    
    if not favs:
        st.info("You haven't saved any programs yet. Go to the Chat to find and save some!")
    else:
        for f in favs:
            with st.expander(f"{f.get('master')} - {f.get('university')}", expanded=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📍 **Location:** {f.get('location', 'N/A')}")
                    st.write(f"💰 **Tuition:** {f.get('tuition', 'N/A')}")
                    st.caption(f"Saved on: {f.get('saved_at', 'Unknown date')}")
                with col2:
                    if st.button("Remove 🗑️", key=f"del_{f.get('master')}"):
                        auth_service.remove_favorite(st.session_state.user_info['username'], f['master'])
                        st.rerun()

elif selected == "calculator":
    render_price_calculator()

elif selected == "map":
    st.markdown(
        "<h2 style='text-align: center; color: #F4B400;'>Top Universities Worldwide</h2>",
        unsafe_allow_html=True,
    )
    render_university_map()
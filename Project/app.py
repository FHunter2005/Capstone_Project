# app.py
# ===========================
# Masters Finder – Chatbot + Calculator
# ===========================
import base64
import json
import os
import time

import streamlit as st
from streamlit_lottie import st_lottie

# --- Custom Services ---
from services.auth_service import AuthService
from calculator import render_price_calculator
from map_tab import render_university_map
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
@st.cache_data
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
    /* =========================================================
       MasterMatch – Sidebar Clean UI (buttons + radio threads)
       ========================================================= */

    /* ---------- Sidebar background ---------- */
    [data-testid="stSidebar"] {{
        background-image:
            linear-gradient(rgba(0,0,0,0.82), rgba(0,0,0,0.92)),
            url("data:image/jpg;base64,{sidebar_bg_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}

    [data-testid="stSidebar"] > div:first-child {{
        background-color: transparent !important;
        padding-top: 10px;
    }}

    /* ---------- Logo ---------- */
    [data-testid="stSidebar"] img.mm-logo {{
        width: 96px;
        border-radius: 18px;
        border: 2px solid rgba(244, 180, 0, 0.75) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
    }}

    /* ---------- Section titles + divider ---------- */
    .mm-section-title {{
        margin-top: 10px;
        margin-bottom: 8px;
        font-size: 12px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.55);
    }}

    .mm-divider {{
        margin: 12px 0;
        border: none;
        height: 1px;
        background: rgba(255,255,255,0.10);
    }}

    /* ---------- Base button style (compact + professional) ---------- */
    .mm-nav [data-testid="stButton"] > button,
    .mm-account [data-testid="stButton"] > button {{
        background: rgba(255,255,255,0.06) !important;
        color: rgba(255,255,255,0.92) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 14px !important;
        padding: 10px 12px !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        width: 100% !important;
        margin: 6px 0 !important;
        transition: background 0.15s ease, border-color 0.15s ease !important;
        text-align: left !important;
    }}

    .mm-nav [data-testid="stButton"] > button:hover,
    .mm-account [data-testid="stButton"] > button:hover {{
        background: rgba(244, 180, 0, 0.10) !important;
        border-color: rgba(244, 180, 0, 0.35) !important;
        transform: none !important;
        box-shadow: none !important;
    }}

    .mm-nav [data-testid="stButton"] > button:focus:not(:active),
    .mm-account [data-testid="stButton"] > button:focus:not(:active) {{
        background: rgba(244, 180, 0, 0.14) !important;
        border-color: rgba(244, 180, 0, 0.45) !important;
        box-shadow: none !important;
        font-weight: 600 !important;
    }}

    /* ---------- Conversation picker (st.radio) ---------- */
    /* Container itself (works when you use st.container(height=..., border=False)) */
    [data-testid="stSidebar"] [role="radiogroup"] {{
        gap: 10px;
    }}

    /* Hide the actual radio circle */
    [data-testid="stSidebar"] [role="radiogroup"] input[type="radio"] {{
        display: none !important;
    }}

    /* Each option becomes a clean "card" row */
    [data-testid="stSidebar"] [role="radiogroup"] label {{
        display: block;
        padding: 12px 14px !important;
        border-radius: 16px !important;
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        transition: background 0.15s ease, border-color 0.15s ease;
        margin: 0 !important;
        overflow: hidden;                /* avoids ugly cut edges */
    }}

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
        background: rgba(244, 180, 0, 0.10) !important;
        border-color: rgba(244, 180, 0, 0.35) !important;
    }}

    /* The text inside label */
    [data-testid="stSidebar"] [role="radiogroup"] label p {{
        margin: 0 !important;
        white-space: pre-line;           /* lets us use \n title + date */
        line-height: 1.25;
        color: rgba(255,255,255,0.92);
    }}

    /* First line (title) – slightly stronger */
    [data-testid="stSidebar"] [role="radiogroup"] label p:first-child {{
        font-size: 15px;
        font-weight: 650;
    }}

    /* Second line (date) – smaller + muted */
    [data-testid="stSidebar"] [role="radiogroup"] label p:last-child {{
        font-size: 12px;
        font-weight: 500;
        color: rgba(255,255,255,0.55);
        margin-top: 4px !important;
    }}

    /* Selected state */
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
        background: rgba(244, 180, 0, 0.14) !important;
        border-color: rgba(244, 180, 0, 0.55) !important;
        box-shadow: 0 0 0 1px rgba(244, 180, 0, 0.18) inset;
    }}

    /* Tighten radio wrapper spacing (Streamlit adds padding sometimes) */
    [data-testid="stSidebar"] div:has(> [role="radiogroup"]) {{
        margin-top: 6px;
    }}

    /* Scrollbar (container area) – subtle */
    [data-testid="stSidebar"] ::-webkit-scrollbar {{
        width: 8px;
    }}
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb {{
        background: rgba(255,255,255,0.14);
        border-radius: 10px;
    }}
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {{
        background: rgba(255,255,255,0.22);
    }}

    /* Optional: make popover buttons look consistent */
    [data-testid="stSidebar"] [data-testid="stPopover"] button {{
        border-radius: 14px !important;
    }}

    /* Scroll area inside the sidebar container */
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {{
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
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
                    threads = auth_service.get_user_threads(username)
                    

                    if threads:
                        st.session_state.current_thread_id = threads[0]["id"]
                        st.session_state.messages = auth_service.load_thread_messages(st.session_state.current_thread_id)
                    else:
                        new_id = auth_service.create_new_thread(username)
                        st.session_state.current_thread_id = new_id
                        st.session_state.messages = []

                    if "agent_client" in st.session_state:
                        del st.session_state.agent_client

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
                    new_id = auth_service.create_new_thread(new_user)
                    st.session_state.current_thread_id = new_id
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
    # Logo
    st.markdown(
        f"""
        <div style="text-align:center; padding: 14px 0 6px;">
            <img src="data:image/png;base64,{logo_base64}" class="mm-logo">
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ACCOUNT
    st.markdown('<div class="mm-section-title">Account</div>', unsafe_allow_html=True)
    st.markdown('<div class="mm-account">', unsafe_allow_html=True)

    user_name = st.session_state.user_info["name"]
    st.markdown(f"<div style='font-size:18px; font-weight:650; margin: 2px 0 8px;'>Hi, {user_name}! 👋</div>", unsafe_allow_html=True)

    if st.button("Logout", key="logout_btn", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # close mm-account
    st.markdown("<hr class='mm-divider'/>", unsafe_allow_html=True)

    # NAVIGATION
    st.markdown('<div class="mm-section-title">Navigation</div>', unsafe_allow_html=True)
    st.markdown('<div class="mm-nav">', unsafe_allow_html=True)

    if st.button("Chat", key="chat_btn", use_container_width=True):
        st.session_state.page = "chat"
        st.rerun()

    if st.button("Calculator", key="calc_btn", use_container_width=True):
        st.session_state.page = "calculator"
        st.rerun()

    if st.button("Map", key="map_btn", use_container_width=True):
        st.session_state.page = "map"
        st.rerun()

    if st.button("Favorites", key="fav_btn", use_container_width=True):
        st.session_state.page = "favorites"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # close mm-nav
    st.markdown("<hr class='mm-divider'/>", unsafe_allow_html=True)

    # CONVERSATIONS
        # CONVERSATIONS
    st.markdown('<div class="mm-section-title">Conversations</div>', unsafe_allow_html=True)

    # Big button
    st.markdown('<div class="mm-nav">', unsafe_allow_html=True)
    if st.button("＋ New Conversation", use_container_width=True, key="new_conv_top"):
        new_id = auth_service.create_new_thread(st.session_state.user_info["username"])
        st.session_state.current_thread_id = new_id
        st.session_state.messages = []
        st.session_state.last_recommended_masters = []
        st.session_state.pop("agent_client", None)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    threads = auth_service.get_user_threads(st.session_state.user_info["username"])

    # Sort newest first (if backend already sorted, no harm)
    try:
        threads = sorted(threads, key=lambda x: x.get("date", ""), reverse=True)
    except Exception:
        pass

    ids = [t["id"] for t in threads]

    def _label(tid: str) -> str:
        t = next(x for x in threads if x["id"] == tid)
        title = (t.get("title") or "Untitled").strip()
        date  = (t.get("date") or "").strip()
        if len(title) > 34:
            title = title[:34] + "…"
        return f"{title}\n{date}"

    if st.session_state.current_thread_id is None and ids:
        st.session_state.current_thread_id = ids[0]

    with st.container(height=360, border=False):
        selected_id = st.radio(
            label="",
            options=ids,
            format_func=_label,
            index=ids.index(st.session_state.current_thread_id) if st.session_state.current_thread_id in ids else 0,
            key="thread_picker",
            label_visibility="collapsed",
        )

    if selected_id != st.session_state.current_thread_id:
        st.session_state.current_thread_id = selected_id
        st.session_state.messages = auth_service.load_thread_messages(selected_id)
        st.session_state.pop("agent_client", None)
        st.rerun()

    # Actions
    c1, c2 = st.columns([1.6, 1.4])

    with c1:
        with st.popover("✏️ Rename", use_container_width=True):
            new_title = st.text_input("New title", value="", placeholder="Type a new title…", key="rename_input")
            if st.button("Save title", key="rename_save"):
                if new_title.strip():
                    auth_service.update_thread_title(st.session_state.current_thread_id, new_title.strip())
                    st.rerun()

    with c2:
        with st.popover("🗑️ Delete", use_container_width=True):
            st.write("Delete this conversation?")
            if st.button("Yes, delete", key="confirm_delete"):
                auth_service.delete_thread(st.session_state.current_thread_id)

                threads2 = auth_service.get_user_threads(st.session_state.user_info["username"])
                if threads2:
                    st.session_state.current_thread_id = threads2[0]["id"]
                    st.session_state.messages = auth_service.load_thread_messages(st.session_state.current_thread_id)
                else:
                    new_id = auth_service.create_new_thread(st.session_state.user_info["username"])
                    st.session_state.current_thread_id = new_id
                    st.session_state.messages = []

                st.session_state.pop("agent_client", None)
                st.rerun()



# ---------- Content Routing ----------
selected = st.session_state.page

if selected == "chat":
    st.markdown("<br>", unsafe_allow_html=True)

    reset_col1, reset_col2 = st.columns([6, 1])
    with reset_col2:
        if st.button("Reset", key="reset_agent_btn", use_container_width=True):
            if "agent_client" in st.session_state:
                del st.session_state.agent_client
            st.rerun()

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

        # 1. Display and Save User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        auth_service.save_message(st.session_state.current_thread_id, "user", prompt)

        if len(st.session_state.messages) == 1:
            # Simple title: first 30 chars of prompt
            new_title = prompt[:30] + "..." if len(prompt) > 30 else prompt
            auth_service.update_thread_title(st.session_state.current_thread_id, new_title)

        # 2. Generate and Stream Assistant Reply
        with st.chat_message("assistant"):
            response = "" # Initialize variable to ensure scope availability
            
            # --- PHASE A: Generation (Back-end logic) ---
            with st.spinner("Thinking..."):
                try:
                    # Check/Init Agent
                    if "agent_client" not in st.session_state:
                        past_history = st.session_state.messages[:-1][-20:]
                        st.session_state.agent_client = AIClient(history_messages=past_history)

                    # Get Response
                    response = st.session_state.agent_client.send_message_to_agent(prompt)

                except Exception as e:
                    # Error Handling / Retry Logic
                    err = str(e).lower()
                    token_related = (
                        "maximum context" in err
                        or "context length" in err
                        or "token" in err
                    )

                    if token_related:
                        if "agent_client" in st.session_state:
                            del st.session_state.agent_client

                        past_history = st.session_state.messages[:-1][-8:]
                        st.session_state.agent_client = AIClient(history_messages=past_history)

                        try:
                            response = st.session_state.agent_client.send_message_to_agent(prompt)
                        except Exception as e2:
                            response = f"Error recovering from context limit: {e2}"
                    else:
                        response = f"Error: {e}"

            # --- PHASE B: Streaming (Front-end visual) ---
            # Now that we have the 'response' string, we stream it
            def stream_data():
                for word in response.split(" "):
                    yield word + " "
                    time.sleep(0.02)
            
            # Write stream actually outputs to the screen here
            st.write_stream(stream_data)

        # 3. Save Assistant Message to State/DB
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
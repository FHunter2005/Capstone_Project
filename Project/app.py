# app.py
# ===========================
# Masters Finder – Chatbot + Calculator
# ===========================

import base64
import json
import os
import time
import requests
from datetime import datetime
import html as html_lib

import streamlit as st
from streamlit_lottie import st_lottie

from dotenv import load_dotenv
load_dotenv()

from langfuse import observe, get_client
import pypdf

# Markdown -> HTML (for chat bubbles formatting)
# pip install markdown-it-py
try:
    from markdown_it import MarkdownIt
except Exception:
    MarkdownIt = None

# --- Custom Services ---
from services.auth_service import AuthService
from calculator import render_price_calculator
from map_tab import render_university_map
from ai.ai_client import AIClient  # kept in case you want to use it later

# --- Constants & Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "extras/photos/mm.png")
LOTTIE_PATH = os.path.join(BASE_DIR, "extras/photos/gif.json")
SIDE_PATH = os.path.join(BASE_DIR, "extras/photos/photo.jpg")

# Optional: place capa.jpg next to app.py
LOGIN_HERO_PATH = os.path.join(BASE_DIR, "extras/photos/capa.jpg")
# Backend URL (use env var in deploy; defaults to local)
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT = f"{BACKEND_BASE_URL.rstrip('/')}/chat"

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

    # onboarding state (NOT forced, no banner)
    if "show_onboarding" not in st.session_state:
        st.session_state.show_onboarding = False


init_state()
auth_service = AuthService()

# ---------- Helper Functions ----------
@st.cache_data
def load_image_base64(path: str, mtime: float = 0.0) -> str:
    """
    mtime param ensures cache refreshes if the file changes.
    Call with mtime=os.path.getmtime(path) when possible.
    """
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
    except Exception:
        return

    container = st.empty()
    st.markdown(
        """
        <style>
        .stLottie iframe { border-radius: 20px !important; overflow: hidden !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with container:
        st_lottie(animation, height=height, key="intro_lottie")

    time.sleep(duration)
    container.empty()


def extract_text_from_pdf(uploaded_file):
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text.strip()
    except Exception:
        return None


def do_logout():
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.messages = []
    st.session_state.last_recommended_masters = []
    st.session_state.current_thread_id = None
    st.session_state.show_onboarding = False

    st.session_state.pop("agent_client", None)
    st.session_state.pop("langfuse", None)
    st.rerun()


def ensure_thread():
    if st.session_state.current_thread_id is None and st.session_state.user_info:
        new_id = auth_service.create_new_thread(st.session_state.user_info["username"])
        st.session_state.current_thread_id = new_id
        st.session_state.messages = []


def refresh_onboarding_flag():
    """Only used to decide the header in Profile page. Never blocks anything."""
    if not st.session_state.user_info:
        st.session_state.show_onboarding = False
        return
    try:
        profile = auth_service.get_profile(st.session_state.user_info["username"]) or {}
        st.session_state.show_onboarding = not profile.get("onboarding_completed", False)
    except Exception:
        st.session_state.show_onboarding = False


def render_recommendations(programs, msg_index):
    """
    Renders the list of programs for a specific message.
    msg_index is used to ensure button keys are unique per message.

    OPTION 1 (implemented): tighter spacing by removing st.divider()
    and using a compact custom <hr>.
    """
    if not programs:
        return

    with st.expander(f"👇 Found {len(programs)} Programs", expanded=True):
        username = st.session_state.user_info["username"]
        current_favs = auth_service.get_user_favorites(username)
        saved_identifiers = {(f.get("master"), f.get("university")) for f in current_favs}

        for i, prog in enumerate(programs):
            c1, c2 = st.columns([4, 1], vertical_alignment="center")
            master_name = prog.get("master", "Unknown Program")
            uni_name = prog.get("university", "Unknown University")

            with c1:
                st.markdown(f"**{master_name}** at *{uni_name}*")
                loc = prog.get("Location") or prog.get("location")
                if loc:
                    st.caption(f"📍 {loc}")

            with c2:
                unique_id = str(prog.get("_id", i))
                btn_key = f"save_{msg_index}_{i}_{unique_id}"

                if (master_name, uni_name) in saved_identifiers:
                    st.button("✅ Saved", key=btn_key, disabled=True, use_container_width=True)
                else:
                    if st.button("❤️ Save", key=btn_key, use_container_width=True):
                        clean_prog = prog.copy()
                        clean_prog["Location"] = prog.get("Location") or prog.get("location") or "N/A"
                        clean_prog["Tuition Fee"] = prog.get("Tuition Fee") or prog.get("tuition") or "N/A"

                        success, msg = auth_service.add_favorite(username, clean_prog)
                        if success:
                            st.toast(f"Saved: {master_name}", icon="✅")
                            time.sleep(0.4)
                            st.rerun()
                        else:
                            st.toast(msg, icon="ℹ️")

            # compact divider (less spacing than st.divider)
            if i != len(programs) - 1:
                st.markdown("<hr class='mm-rec-divider'/>", unsafe_allow_html=True)


# ---------- Custom chat bubbles (assistant LEFT, user RIGHT) ----------
# Markdown renderer (safe: HTML disabled). Falls back to basic escaping if missing.
MD_RENDERER = None
if MarkdownIt is not None:
    MD_RENDERER = MarkdownIt("commonmark", {"html": False, "breaks": True})


def _to_bubble_html(text: str) -> str:
    """
    Convert Markdown -> safe HTML (no raw HTML allowed).
    Supports **bold**, lists, numbered lists, etc.
    If markdown-it-py isn't installed, fallback to plain escaped text w/ line breaks.
    """
    t = text or ""
    if MD_RENDERER is None:
        return html_lib.escape(t).replace("\n", "<br>")
    return MD_RENDERER.render(t)


def render_chat_bubble(role: str, content: str):
    body = _to_bubble_html(content)

    if role == "user":
        st.markdown(
            f"""
            <div class="mm-chat-row mm-user">
                <div class="mm-bubble mm-user-bubble">{body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="mm-chat-row mm-assistant">
                <div class="mm-avatar">MM</div>
                <div class="mm-bubble mm-assistant-bubble">{body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_assistant_stream_placeholder(placeholder, partial_text: str):
    body = _to_bubble_html(partial_text)
    placeholder.markdown(
        f"""
        <div class="mm-chat-row mm-assistant">
            <div class="mm-avatar">MM</div>
            <div class="mm-bubble mm-assistant-bubble">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Optional tracing if you later switch to AIClient direct calls
@observe(name="User_Chat_Turn")
def traced_chat_turn(prompt: str, username: str, thread_id: str, agent_client) -> str:
    langfuse = get_client()
    langfuse.update_current_trace(
        user_id=username,
        session_id=str(thread_id),
        tags=["streamlit", "chat"],
        metadata={
            "environment": os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "dev"),
            "app": "MasterMatch",
            "page": "chat",
        },
    )
    with langfuse.start_as_current_observation(
        as_type="span",
        name="agent_call",
        input={"prompt": prompt},
    ):
        return agent_client.send_message_to_agent(prompt)


# ---------- Load Assets ----------
logo_mtime = os.path.getmtime(LOGO_PATH) if os.path.exists(LOGO_PATH) else 0
side_mtime = os.path.getmtime(SIDE_PATH) if os.path.exists(SIDE_PATH) else 0
hero_mtime = os.path.getmtime(LOGIN_HERO_PATH) if os.path.exists(LOGIN_HERO_PATH) else 0

logo_base64 = load_image_base64(LOGO_PATH, logo_mtime)
sidebar_bg_base64 = load_image_base64(SIDE_PATH, side_mtime)
hero_base64 = load_image_base64(LOGIN_HERO_PATH, hero_mtime) or sidebar_bg_base64

# ---------- Show Lottie Intro ----------
play_lottie_intro(LOTTIE_PATH, height=300, width=300, duration=6)

# ---------- Global CSS ----------
st.markdown(
    f"""
    <style>
    /* Top + bottom bars color (Streamlit chrome) */
    header[data-testid="stHeader"] {{
        background: rgba(10, 14, 22, 0.92) !important;
        border-bottom: 1px solid rgba(244,180,0,0.20) !important;
    }}
    [data-testid="stToolbar"] {{
        background: transparent !important;
    }}
    /* Bottom container varies by Streamlit version; target common selectors */
    [data-testid="stBottomBlockContainer"],
    [data-testid="stBottom"] {{
        background: rgba(10, 14, 22, 0.92) !important;
        border-top: 1px solid rgba(244,180,0,0.20) !important;
    }}

    /* Sidebar background */
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

    [data-testid="stSidebar"] img.mm-logo {{
        width: 96px;
        border-radius: 18px;
        border: 2px solid rgba(244, 180, 0, 0.75) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
    }}

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
        white-space: nowrap !important;
    }}

    .mm-nav [data-testid="stButton"] > button:hover,
    .mm-account [data-testid="stButton"] > button:hover {{
        background: rgba(244, 180, 0, 0.10) !important;
        border-color: rgba(244, 180, 0, 0.35) !important;
    }}

    /* spacing: logo block */
    .mm-logo-wrap {{
        text-align: center;
        padding: 18px 0 6px;
        margin-bottom: 14px;
    }}

    /* conversations spacing */
    [data-testid="stSidebar"] [role="radiogroup"] {{
        display: flex !important;
        flex-direction: column !important;
        gap: 14px !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] input[type="radio"] {{
        display: none !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label {{
        display: block;
        padding: 14px 16px !important;
        border-radius: 16px !important;
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        margin: 0 !important;
        overflow: hidden;
        transition: background 0.15s ease, border-color 0.15s ease;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
        background: rgba(244, 180, 0, 0.10) !important;
        border-color: rgba(244, 180, 0, 0.35) !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label p {{
        margin: 0 !important;
        white-space: pre-line;
        line-height: 1.25;
        color: rgba(255,255,255,0.92);
        overflow-wrap: anywhere !important;
        word-break: break-word !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label p:first-child {{
        font-size: 15px;
        font-weight: 650;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label p:last-child {{
        font-size: 12px;
        font-weight: 500;
        color: rgba(255,255,255,0.55);
        margin-top: 4px !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
        background: rgba(244, 180, 0, 0.14) !important;
        border-color: rgba(244, 180, 0, 0.55) !important;
        box-shadow: 0 0 0 1px rgba(244, 180, 0, 0.18) inset;
    }}

    /* scrollbar */
    [data-testid="stSidebar"] ::-webkit-scrollbar {{ width: 8px; }}
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb {{
        background: rgba(255,255,255,0.14);
        border-radius: 10px;
    }}
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {{
        background: rgba(255,255,255,0.22);
    }}

    /* --------- CHAT (assistant LEFT, user RIGHT) --------- */
    .mm-chat-container {{
        max-width: 920px;
        margin: 0 auto;
        padding: 0 10px;
    }}

    .mm-chat-row {{
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin: 12px 0;
    }}

    .mm-user {{
        justify-content: flex-end;
    }}

    .mm-assistant {{
        justify-content: flex-start;
    }}

    .mm-avatar {{
        width: 36px;
        height: 36px;
        border-radius: 12px;
        display: grid;
        place-items: center;
        font-weight: 800;
        font-size: 12px;
        color: rgba(255,255,255,0.92);
        background: linear-gradient(135deg, rgba(244,180,0,0.35), rgba(167,139,250,0.35));
        border: 1px solid rgba(255,255,255,0.10);
        flex: 0 0 36px;
        margin-top: 2px;
    }}

    .mm-bubble {{
        border-radius: 18px;
        padding: 14px 16px;
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 10px 30px rgba(0,0,0,0.18);
        line-height: 1.55;
        font-size: 15px;
        max-width: min(720px, 88%);
        backdrop-filter: blur(6px);
    }}

    .mm-assistant-bubble {{
        background: rgba(255,255,255,0.08) !important;
        color: rgba(255,255,255,0.94) !important;
    }}

    .mm-user-bubble {{
        background: rgba(17, 24, 39, 0.68) !important;
        color: rgba(255,255,255,0.96) !important;
    }}

    /* Markdown inside bubbles */
    .mm-bubble p {{ margin: 0 0 10px 0; }}
    .mm-bubble p:last-child {{ margin-bottom: 0; }}

    .mm-bubble ul, .mm-bubble ol {{
        margin: 8px 0 8px 22px;
        padding: 0;
    }}
    .mm-bubble li {{ margin: 4px 0; }}
    .mm-bubble strong {{ font-weight: 800; }}

    .mm-bubble pre {{
        margin: 10px 0;
        padding: 12px 14px;
        border-radius: 14px;
        background: rgba(0,0,0,0.30);
        border: 1px solid rgba(255,255,255,0.10);
        overflow-x: auto;
    }}
    .mm-bubble code {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}

    /* Compact divider for recommendations */
    .mm-rec-divider {{
        margin: 10px 0;
        border: none;
        height: 1px;
        background: rgba(255,255,255,0.10);
    }}

    /* Hide Streamlit chat action buttons if any appear */
    [data-testid="stChatMessage"] [data-testid="stChatMessageActionButtons"],
    [data-testid="stChatMessage"] [data-testid="stChatMessageActionButton"],
    [data-testid="stChatMessage"] [data-testid^="stChatMessageAction"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- AUTH SCREEN (new login page) ----------
if not st.session_state.logged_in:
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"], div[data-testid="collapsedControl"] {{
            display: none !important;
        }}
        header, footer {{ visibility: hidden; }}

        .block-container {{
            padding-top: 2.2rem !important;
            padding-bottom: 2.2rem !important;
            max-width: 1180px !important;
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, #f7f7f7 0%, #f2f1ea 45%, #f3e6c0 100%) !important;
        }}

        div[data-testid="column"]:has(.mm-auth-left-marker),
        div[data-testid="stColumn"]:has(.mm-auth-left-marker) {{
            background: rgba(255,255,255,0.72) !important;
            border: 1px solid rgba(0,0,0,0.06) !important;
            border-radius: 28px !important;
            padding: 38px 38px 32px !important;
            box-shadow: 0 18px 44px rgba(0,0,0,0.10) !important;
            backdrop-filter: blur(10px) !important;
        }}

        .mm-auth-title {{
            font-size: 34px;
            font-weight: 900;
            text-align: center;
            color: rgba(0,0,0,0.86);
        }}
        .mm-auth-sub {{
            text-align: center;
            color: rgba(0,0,0,0.55);
            font-size: 14px;
            margin-bottom: 18px;
        }}

        /* tabs text visibility */
        div[data-testid="stTabs"] button[role="tab"] *,
        div[data-testid="stTabs"] button[role="tab"] p,
        div[data-testid="stTabs"] button[role="tab"] span {{
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] * {{
            color: #ff4b4b !important;
            -webkit-text-fill-color: #ff4b4b !important;
        }}
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
            background-color: #ff4b4b !important;
        }}

        [data-testid="stTextInput"] input {{
            border-radius: 14px !important;
        }}
        .stButton > button {{
            border-radius: 14px !important;
            background: #111827 !important;
            color: white !important;
            font-weight: 900 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.44, 0.56], gap="large")

    with left:
        st.markdown('<div class="mm-auth-left-marker"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="text-align:center; margin-bottom:10px;">
                <img src="data:image/png;base64,{logo_base64}"
                     style="width:88px; border-radius:24px; border:2px solid #F4B400;"/>
            </div>
            <div class="mm-auth-title">Welcome to MasterMatch</div>
            <div class="mm-auth-sub">Sign in or create an account to continue.</div>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2 = st.tabs(["Sign in", "Create account"])

        with tab1:
            username = st.text_input("Username", key="login_user", placeholder="Your username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••••")

            if st.button("Sign in", use_container_width=True, key="login_btn"):
                user = auth_service.login_user(username, password)
                if user:

                    token = auth_service.create_access_token(data={"sub": username})

                    st.session_state.auth_token = token
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.page = "chat"

                    refresh_onboarding_flag()

                    threads = auth_service.get_user_threads(username)
                    if threads:
                        st.session_state.current_thread_id = threads[0]["id"]
                        st.session_state.messages = auth_service.load_thread_messages(st.session_state.current_thread_id)
                    else:
                        new_id = auth_service.create_new_thread(username)
                        st.session_state.current_thread_id = new_id
                        st.session_state.messages = []

                    st.session_state.pop("agent_client", None)
                    st.session_state.pop("langfuse", None)
                    st.rerun()
                else:
                    st.error("Incorrect credentials.")

        with tab2:
            new_user = st.text_input("New Username", key="signup_user", placeholder="Choose a username")
            new_name = st.text_input("Your Name", key="signup_name", placeholder="Your full name")
            new_pass = st.text_input("New Password", type="password", key="signup_pass", placeholder="Create a strong password")

            if st.button("Create account", use_container_width=True, key="signup_btn"):
                success, msg = auth_service.register_user(new_user, new_name, new_pass)
                if success:
                    
                    token = auth_service.create_access_token(data={"sub": new_user})

                    st.session_state.auth_token = token
                    st.session_state.logged_in = True
                    st.session_state.user_info = {"username": new_user, "name": new_name}
                    st.session_state.page = "chat"

                    st.session_state.show_onboarding = True

                    st.session_state.messages = []
                    new_id = auth_service.create_new_thread(new_user)
                    st.session_state.current_thread_id = new_id

                    st.session_state.pop("agent_client", None)
                    st.session_state.pop("langfuse", None)

                    st.success("Account created successfully! Redirecting…")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error(msg)

    with right:
        st.markdown(
            f"""
            <div style="border-radius:28px; overflow:hidden; box-shadow:0 18px 44px rgba(0,0,0,0.12); height:560px;">
                <div style="
                    width:100%;
                    height:100%;
                    background-image:url('data:image/jpg;base64,{hero_base64}');
                    background-size:cover;
                    background-position:center;
                    position:relative;
                ">
                    <div style="
                        position:absolute;
                        bottom:22px; left:22px; right:22px;
                        background:rgba(255,255,255,0.18);
                        backdrop-filter:blur(10px);
                        border-radius:22px;
                        padding:16px;
                        color:white;
                    ">
                        <h3 style="margin:0; font-size:18px; font-weight:900;">Find the right Master’s program</h3>
                        <p style="margin:6px 0 0 0; font-size:13px;">
                            Consult with AI • Compare costs • Map your future
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.stop()


# ---------- Main App Header ----------
header_html = f"""
<div style="text-align: center; padding-top: 10px; padding-bottom: 10px;">
    <img src="data:image/png;base64,{logo_base64}" style="width:200px; border-radius:12px;"/>
    <h1 style="color:#F4B400; margin-top:20px; font-weight:700; font-size:48px;">MasterMatch</h1>
    <p style="font-size:20px; color:lightgray; margin-top:-10px;">Your personal AI advisor for master’s programs.</p>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)


# ---------- Sidebar Navigation ----------
with st.sidebar:
    st.markdown(
        f"""
        <div class="mm-logo-wrap">
            <img src="data:image/png;base64,{logo_base64}" class="mm-logo">
        </div>
        """,
        unsafe_allow_html=True,
    )

    username = st.session_state.user_info["username"]
    user_name = st.session_state.user_info["name"]

    with st.popover("Profile", use_container_width=True):
        st.markdown(f"**Hi, {user_name}!**")
        if st.button("Favorites", use_container_width=True, key="pop_favs"):
            st.session_state.page = "favorites"
            st.rerun()
        if st.button("Profile (Q&A)", use_container_width=True, key="pop_profile"):
            st.session_state.page = "profile"
            st.rerun()
        if st.button("Logout", use_container_width=True, key="pop_logout"):
            do_logout()

    st.markdown("<hr class='mm-divider'/>", unsafe_allow_html=True)

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

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<hr class='mm-divider'/>", unsafe_allow_html=True)

    if st.session_state.page == "chat":
        st.markdown('<div class="mm-section-title">Conversations</div>', unsafe_allow_html=True)

        st.markdown('<div class="mm-nav">', unsafe_allow_html=True)
        if st.button("＋ New Conversation", use_container_width=True, key="new_conv_top"):
            new_id = auth_service.create_new_thread(username)
            st.session_state.current_thread_id = new_id
            st.session_state.messages = []
            st.session_state.last_recommended_masters = []
            st.session_state.pop("agent_client", None)
            st.session_state.pop("langfuse", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        threads = auth_service.get_user_threads(username)
        try:
            threads = sorted(threads, key=lambda x: x.get("date", ""), reverse=True)
        except Exception:
            pass

        ids = [t["id"] for t in threads]

        def _label(tid: str) -> str:
            t = next(x for x in threads if x["id"] == tid)
            title = (t.get("title") or "Untitled").strip()
            date = (t.get("date") or "").strip()
            if len(title) > 34:
                title = title[:34] + "…"
            return f"{title}\n{date}"

        if st.session_state.current_thread_id is None and ids:
            st.session_state.current_thread_id = ids[0]

        if ids:
            with st.container(height=360, border=False):
                selected_id = st.radio(
                    label="",
                    options=ids,
                    format_func=_label,
                    index=ids.index(st.session_state.current_thread_id)
                    if st.session_state.current_thread_id in ids
                    else 0,
                    key="thread_picker",
                    label_visibility="collapsed",
                )

            if selected_id != st.session_state.current_thread_id:
                st.session_state.current_thread_id = selected_id
                st.session_state.messages = auth_service.load_thread_messages(selected_id)
                st.session_state.pop("agent_client", None)
                st.session_state.pop("langfuse", None)
                st.rerun()

        c1, c2 = st.columns([1.6, 1.4])
        with c1:
            with st.popover("✏️ Rename", use_container_width=True):
                new_title = st.text_input("New title", value="", placeholder="Type a new title…", key="rename_input")
                if st.button("Save title", key="rename_save"):
                    if new_title.strip() and st.session_state.current_thread_id:
                        auth_service.update_thread_title(st.session_state.current_thread_id, new_title.strip())
                        st.rerun()

        with c2:
            with st.popover("🗑️ Delete", use_container_width=True):
                st.write("Delete this conversation?")
                if st.button("Yes, delete", key="confirm_delete"):
                    if st.session_state.current_thread_id:
                        auth_service.delete_thread(st.session_state.current_thread_id)

                    threads2 = auth_service.get_user_threads(username)
                    if threads2:
                        st.session_state.current_thread_id = threads2[0]["id"]
                        st.session_state.messages = auth_service.load_thread_messages(st.session_state.current_thread_id)
                    else:
                        new_id = auth_service.create_new_thread(username)
                        st.session_state.current_thread_id = new_id
                        st.session_state.messages = []

                    st.session_state.pop("agent_client", None)
                    st.session_state.pop("langfuse", None)
                    st.rerun()


# ---------- Content Routing ----------
selected = st.session_state.page

if selected == "profile":
    refresh_onboarding_flag()
    current_profile = auth_service.get_profile(username) or {}

    if st.session_state.show_onboarding:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>🎉 Welcome to MasterMatch!</h1>", unsafe_allow_html=True)
        st.markdown(
            "<h4 style='text-align: center; color: gray;'>Let's get to know you to provide better recommendations.</h4>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='text-align: center; color: #F4B400;'>My Student Profile 🎓</h2>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📄 Upload CV (Fast)", "✍️ Manual Q&A (Detailed)"])

    with tab1:
        st.info("Upload your CV (PDF). You can upload multiple files to build a comprehensive profile.")

        saved_docs = current_profile.get("cv_documents", [])
        if not saved_docs and current_profile.get("cv_text"):
            saved_docs = [{"name": "Previous Upload", "text": current_profile["cv_text"], "date": "Unknown"}]

        if saved_docs:
            st.write("### 📂 Uploaded Documents")
            for i, doc in enumerate(saved_docs):
                with st.container(border=True):
                    c1, c2 = st.columns([0.85, 0.15])
                    with c1:
                        st.write(f"📄 **{doc.get('name', 'Untitled')}**")
                        st.caption(f"Uploaded: {doc.get('date', 'Unknown')}")
                    with c2:
                        if st.button("🗑️", key=f"del_cv_{i}"):
                            saved_docs.pop(i)
                            full_text = "\n\n".join([d["text"] for d in saved_docs])
                            auth_service.update_profile(username, {
                                "cv_documents": saved_docs,
                                "cv_text": full_text
                            })
                            st.rerun()
            st.divider()

        uploaded_file = st.file_uploader("Add a PDF file", type="pdf")

        if uploaded_file is not None:
            if st.button("Analyze CV & Save", use_container_width=True):
                with st.spinner("Reading PDF..."):
                    text = extract_text_from_pdf(uploaded_file)

                if text:
                    new_doc = {
                        "name": uploaded_file.name,
                        "text": text,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }

                    updated_docs = saved_docs + [new_doc]
                    combined_text = "\n\n".join([d["text"] for d in updated_docs])

                    success, msg = auth_service.update_profile(
                        username,
                        {
                            "cv_documents": updated_docs,
                            "cv_text": combined_text,
                            "onboarding_completed": True
                        },
                    )
                    if success:
                        st.success(f"'{uploaded_file.name}' uploaded successfully!")

                        if st.session_state.current_thread_id is None:
                            new_id = auth_service.create_new_thread(username)
                            st.session_state.current_thread_id = new_id
                            st.session_state.messages = []

                        welcome_msg = (
                            f"I've received your CV (**{uploaded_file.name}**)! 📄\n\n"
                            "Now that I know your background, skills, and experience, I can provide much better recommendations. "
                            "Try asking: **'Based on my CV, which Master's programs fit me best?'**"
                        )

                        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                        auth_service.save_message(st.session_state.current_thread_id, "assistant", welcome_msg)

                        st.session_state.show_onboarding = False
                        time.sleep(1.0)
                        st.session_state.page = "chat"
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Could not read text from this PDF.")

    with tab2:
        with st.form("profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                bg = st.text_input("Undergraduate Major", value=current_profile.get("background", ""))
                gpa = st.number_input("GPA (0-20)", value=float(current_profile.get("gpa", 0.0)))
                city = st.text_input("City of Preference", value=current_profile.get("city", ""))

            with col2:
                budget = st.number_input("Max Budget (€)", value=int(current_profile.get("budget", 0)))
                exp = st.selectbox(
                    "Experience",
                    ["0-1 years", "1-3 years", "3-5 years", "5+ years"],
                    index=["0-1 years", "1-3 years", "3-5 years", "5+ years"].index(
                        current_profile.get("experience", "0-1 years")
                    )
                    if current_profile.get("experience") in ["0-1 years", "1-3 years", "3-5 years", "5+ years"]
                    else 0,
                )

            interests = st.text_area("Career Interests", value=current_profile.get("interests", ""))

            submitted = st.form_submit_button("Save Profile", use_container_width=True)
            if submitted:
                profile_data = {
                    "background": bg,
                    "gpa": gpa,
                    "city": city,
                    "budget": budget,
                    "experience": exp,
                    "interests": interests,
                    "onboarding_completed": True,
                }
                if "cv_text" in current_profile:
                    profile_data["cv_text"] = current_profile["cv_text"]
                if "cv_documents" in current_profile:
                    profile_data["cv_documents"] = current_profile["cv_documents"]

                success, msg = auth_service.update_profile(username, profile_data)
                if success:
                    st.success("Profile Saved!")
                    st.session_state.show_onboarding = False
                    time.sleep(0.6)
                    st.session_state.page = "chat"
                    st.rerun()
                else:
                    st.error(msg)

    if st.session_state.show_onboarding:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Skip for now (I'll do it later)", type="secondary", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()

elif selected == "chat":
    ensure_thread()
    st.markdown("<br>", unsafe_allow_html=True)

    reset_col1, reset_col2 = st.columns([6, 1])
    with reset_col2:
        if st.button("Reset", key="reset_agent_btn", use_container_width=True):
            st.session_state.pop("agent_client", None)
            st.session_state.pop("langfuse", None)
            st.rerun()

    # --- 1. RENDER HISTORY (CUSTOM BUBBLES + TABLES) ---
    st.markdown('<div class="mm-chat-container">', unsafe_allow_html=True)
    for i, message in enumerate(st.session_state.messages):
        render_chat_bubble(message["role"], message["content"])
        if message.get("data"):
            render_recommendations(message["data"], msg_index=i)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 2. INPUT HANDLING ---
    prompt = st.chat_input("Ask me about master's programs...")

    if prompt:
        # Append User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        auth_service.save_message(st.session_state.current_thread_id, "user", prompt)

        # Rename thread if needed
        if len([m for m in st.session_state.messages if m["role"] == "user"]) == 1:
            new_title = prompt[:30] + "..." if len(prompt) > 30 else prompt
            auth_service.update_thread_title(st.session_state.current_thread_id, new_title)

        # Show user bubble immediately
        st.markdown('<div class="mm-chat-container">', unsafe_allow_html=True)
        render_chat_bubble("user", prompt)

        assistant_placeholder = st.empty()

        # --- 3. GENERATE RESPONSE ---
        response = ""
        found_data = []

        with st.spinner("Thinking..."):
            try:
                clean_history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                ]

                headers = {
                    "Authorization": f"Bearer {st.session_state.get('auth_token', '')}"
                }

                payload = {
                    "username": username,
                    "message": prompt,
                    "thread_id": st.session_state.current_thread_id,
                    "history": clean_history,
                }

                api_response = requests.post(
                    CHAT_ENDPOINT, 
                    json=payload, 
                    headers=headers, 
                    timeout=120
                )

                if api_response.status_code == 200:
                    data = api_response.json()
                    response = data.get("response", "")
                    found_data = data.get("data", []) or []

                elif api_response.status_code == 401:
                    st.error("Session expired. Please log in again.")
                    do_logout()
                    
                else:
                    response = f"⚠️ API Error: {api_response.text}"

            except Exception as e:
                response = f"❌ Error: {e}"

        # Stream assistant bubble (works with markdown too)
        partial = ""
        words = response.split(" ")
        for idx, w in enumerate(words):
            partial += w + " "
            if idx % 4 == 0 or idx == len(words) - 1:
                render_assistant_stream_placeholder(assistant_placeholder, partial.strip())
                time.sleep(0.01)

        # Render table for new response
        if found_data:
            render_recommendations(found_data, msg_index=len(st.session_state.messages))

        st.markdown("</div>", unsafe_allow_html=True)

        # --- 4. SAVE TO STATE & DB ---
        st.session_state.messages.append({"role": "assistant", "content": response, "data": found_data})
        auth_service.save_message(st.session_state.current_thread_id, "assistant", response)

elif selected == "favorites":
    st.markdown("<h2 style='text-align: center; color: #F4B400;'>My Favorite Programs ❤️</h2>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    favs = auth_service.get_user_favorites(username)

    if not favs:
        st.info("You haven't saved any programs yet. Go to the Chat to find and save some!")
    else:
        for i, f in enumerate(favs):
            with st.expander(f"{f.get('master')} - {f.get('university')}", expanded=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📍 **Location:** {f.get('location', f.get('Location', 'N/A'))}")
                    st.write(f"💰 **Tuition:** {f.get('tuition', f.get('Tuition Fee', 'N/A'))}")

                    about_text = f.get("about", "No description available.")
                    st.markdown(f"**📖 About:**\n{about_text}")

                    st.caption(f"Saved on: {f.get('saved_at', 'Unknown date')}")

                with col2:
                    unique_key = f"del_{f.get('master')}_{f.get('university')}_{i}"
                    if st.button("Remove 🗑️", key=unique_key):
                        auth_service.remove_favorite(username, f.get("master"), f.get("university"))
                        st.rerun()

elif selected == "calculator":
    render_price_calculator()

elif selected == "map":
    st.markdown("<h2 style='text-align: center; color: #F4B400;'>Top Universities Worldwide</h2>", unsafe_allow_html=True)
    render_university_map()

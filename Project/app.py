# app.py
# ===========================
# Masters Finder – Chatbot + Calculator
# ===========================

import base64
import json
import os
import time
import requests

import streamlit as st
from streamlit_lottie import st_lottie

from dotenv import load_dotenv
load_dotenv()

from langfuse import observe, get_client
import pypdf

# --- Custom Services ---
from services.auth_service import AuthService
from calculator import render_price_calculator
from map_tab import render_university_map
from ai.ai_client import AIClient  # kept in case you want to use it later

# --- Constants & Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "mm.jpg")
LOTTIE_PATH = os.path.join(BASE_DIR, "gif.json")
SIDE_PATH = os.path.join(BASE_DIR, "photo.jpg")

# Optional: place login_hero.jpg next to app.py
LOGIN_HERO_PATH = os.path.join(BASE_DIR, "login_hero.jpg")

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
logo_base64 = load_image_base64(LOGO_PATH)
sidebar_bg_base64 = load_image_base64(SIDE_PATH)
hero_base64 = load_image_base64(LOGIN_HERO_PATH) or sidebar_bg_base64

# ---------- Show Lottie Intro ----------
play_lottie_intro(LOTTIE_PATH, height=300, width=300, duration=6)


# ---------- Global CSS ----------
st.markdown(
    f"""
    <style>
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
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.page = "chat"

                    # profile completion flag only (no banner)
                    refresh_onboarding_flag()

                    # threads
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
                    st.session_state.logged_in = True
                    st.session_state.user_info = {"username": new_user, "name": new_name}
                    st.session_state.page = "chat"

                    st.session_state.show_onboarding = True  # they can do it later via Profile (Q&A)

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
                            Chat with AI • Compare tuition • Explore universities on the map
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

    # PROFILE POPOVER (Favorites + Logout + Profile Q&A like before)
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

    # NAVIGATION (keep clean)
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

    # CONVERSATIONS (ONLY ON CHAT PAGE)
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
        st.info("Upload your CV (PDF) and we will automatically extract your details.")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

        if uploaded_file is not None:
            if st.button("Analyze CV & Save", use_container_width=True):
                with st.spinner("Reading PDF..."):
                    text = extract_text_from_pdf(uploaded_file)

                if text:
                    success, msg = auth_service.update_profile(
                        username,
                        {"cv_text": text, "onboarding_completed": True},
                    )
                    if success:
                        st.success("CV uploaded successfully!")
                        st.session_state.show_onboarding = False
                        time.sleep(0.6)
                        st.session_state.page = "chat"
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Could not read text from this PDF.")

    with tab2:
        current_profile = auth_service.get_profile(username) or {}

        with st.form("profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                bg = st.text_input("Undergraduate Major", value=current_profile.get("background", ""))
                gpa = st.number_input("GPA (0-20)", value=float(current_profile.get("gpa", 0.0)))
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
                    "budget": budget,
                    "experience": exp,
                    "interests": interests,
                    "onboarding_completed": True,
                }
                if "cv_text" in current_profile:
                    profile_data["cv_text"] = current_profile["cv_text"]

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

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask me about master's programs...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        auth_service.save_message(st.session_state.current_thread_id, "user", prompt)

        # rename thread once on first user message
        if len([m for m in st.session_state.messages if m["role"] == "user"]) == 1:
            new_title = prompt[:30] + "..." if len(prompt) > 30 else prompt
            auth_service.update_thread_title(st.session_state.current_thread_id, new_title)

        with st.chat_message("assistant"):
            response = ""
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "username": username,
                        "message": prompt,
                        "thread_id": st.session_state.current_thread_id,
                        "history": st.session_state.messages[:-1],
                    }
                    api_response = requests.post(CHAT_ENDPOINT, json=payload, timeout=120)

                    if api_response.status_code == 200:
                        data = api_response.json()
                        response = data.get("response", "")

                        found_data = data.get("data", []) or []
                        if found_data:
                            st.session_state.last_recommended_masters = found_data
                    else:
                        response = f"⚠️ API Error: {api_response.text}"

                except Exception as e:
                    response = f"❌ Error: {e}"

            def stream_data():
                for word in response.split(" "):
                    yield word + " "
                    time.sleep(0.02)

            st.write_stream(stream_data)

        st.session_state.messages.append({"role": "assistant", "content": response})
        auth_service.save_message(st.session_state.current_thread_id, "assistant", response)

    # Found programs
    if st.session_state.last_recommended_masters:
        st.markdown("---")
        with st.expander("👇 **Found Programs (Click to Expand/Collapse)**", expanded=True):
            current_favs = auth_service.get_user_favorites(username)
            saved_identifiers = {(f.get("master"), f.get("university")) for f in current_favs}

            for i, prog in enumerate(st.session_state.last_recommended_masters):
                with st.container():
                    c1, c2 = st.columns([4, 1])
                    master_name = prog.get("master", "Unknown Program")
                    uni_name = prog.get("university", "Unknown University")

                    with c1:
                        st.markdown(f"**{master_name}** at *{uni_name}*")

                    with c2:
                        unique_id = str(prog.get("_id", i))
                        btn_key = f"save_{unique_id}_{i}"

                        if (master_name, uni_name) in saved_identifiers:
                            st.button("✅ Saved", key=btn_key, disabled=True)
                        else:
                            if st.button("❤️ Save", key=btn_key):
                                clean_prog = prog.copy()
                                clean_prog["Location"] = prog.get("Location") or prog.get("location") or "N/A"
                                clean_prog["Tuition Fee"] = prog.get("Tuition Fee") or prog.get("tuition") or "N/A"

                                success, msg = auth_service.add_favorite(username, clean_prog)
                                if success:
                                    st.toast(f"Saved: {master_name} ({uni_name})", icon="✅")
                                    time.sleep(0.6)
                                    st.rerun()
                                else:
                                    st.toast(msg, icon="ℹ️")

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

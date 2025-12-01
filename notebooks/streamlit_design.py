# ===========================
# Masters Finder – Chatbot + Calculator
# ===========================
import os
from pathlib import Path
from map_tab import render_university_map  
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from dotenv import load_dotenv
import google.generativeai as genai

# ---------- Paths & env ----------
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "masters.csv"

load_dotenv(dotenv_path=ENV_PATH, override=True)
API_KEY = os.getenv("GOOGLE_API_KEY")

# 🔹 System prompt for the advisor (NEW: we’ll attach this to the model)
ADVISOR_SYSTEM_PROMPT = """
You are a academic advisor for master’s programs in Portugal.
Give practical advice about fields, rankings, tuition,
living costs, scholarships, and choosing between options.
"""

# 🔹 Configure Gemini model using the NEW API pattern
if API_KEY:
    genai.configure(api_key=API_KEY)
    GEM_MODEL = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=ADVISOR_SYSTEM_PROMPT,
    )
else:
    GEM_MODEL = None

# ---------- Synthetic Masters dataset ----------
SAMPLE_COUNTRIES = ["Portugal", "Spain", "France", "Germany", "Netherlands"]
SAMPLE_FIELDS   = ["Data Science", "Economics", "Engineering", "Management", "Statistics"]
SAMPLE_MODALITY = ["On-campus", "Online", "Hybrid"]
SAMPLE_LANG     = ["English", "Portuguese", "Spanish", "French", "German"]

def _make_sample(n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "program_id": np.arange(1, n + 1),
        "program": [f"Master Program {i}" for i in range(1, n + 1)],
        "university": [f"University {i % 12 + 1}" for i in range(1, n + 1)],
        "country": rng.choice(SAMPLE_COUNTRIES, n),
        "field": rng.choice(SAMPLE_FIELDS, n),
        "modality": rng.choice(SAMPLE_MODALITY, n),
        "language": rng.choice(SAMPLE_LANG, n),
        "duration_months": rng.integers(12, 30, n),
        "credits_ects": rng.integers(60, 150, n),
        "ranking": rng.integers(1, 500, n),
        "tuition_total": rng.integers(2500, 35000, n),
        "application_fee": rng.integers(0, 200, n),
        "scholarship_max_pct": rng.integers(0, 60, n),
        "living_cost_month": rng.integers(600, 1600, n),
    })
    return df

def ensure_dataset() -> str:
    DATA_DIR.mkdir(exist_ok=True)
    if not CSV_PATH.exists():
        _make_sample().to_csv(CSV_PATH, index=False)
    return str(CSV_PATH)

@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    ensure_dataset()
    df = pd.read_csv(CSV_PATH)
    df["program_id"] = df["program_id"].astype(str)
    return df

# ---------- Session state ----------
def init_state():
    ss = st.session_state
    ss.setdefault("messages", [])  # [{"role": "user"/"assistant", "content": "..."}]
    # ss["chat"] will be created lazily when the first prompt arrives

# ---------- Layout ----------
st.set_page_config(page_title="MastersMatch", page_icon="🎓", layout="wide")
init_state()

# --- HEADER WITH CENTERED LOGO ---
from pathlib import Path
import base64

# Get path to image
LOGO_PATH = Path(__file__).parent / "Maste Match (2).png"

# Convert to base64 (HTML <img> works reliably this way)
with open(LOGO_PATH, "rb") as f:
    logo_base64 = base64.b64encode(f.read()).decode()

header_html = f"""
<div style="text-align: center; padding-top: 30px; padding-bottom: 10px;">
    <img src="data:image/png;base64,{logo_base64}"
         style="width:200px; border-radius:12px;"/>
    <h1 style="
        color: #F4B400;
        margin-top: 20px;
        font-weight: 700;
        font-size: 48px;
    ">MastersMatch</h1>
    <p style="
        font-size: 20px;
        color: lightgray;
        margin-top: -10px;
    ">Your personal AI advisor for master’s programs.</p>
</div>
"""

st.markdown(header_html, unsafe_allow_html=True)



tab_chat, tab_price, tab_map = st.tabs(
    [" Chat about Masters", "Price Calculator", "Map"]
)
# ---------- TAB 1: Chat about Masters ----------
with tab_chat:
    df = load_data()

    st.subheader("Chat with your study advisor")

    # Show previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # --- Chat loop ---
    if prompt := st.chat_input("Ask anything about master's degrees"):
        # 1) Show + store user message
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2) Get assistant response from Gemini
        if GEM_MODEL is None:
            answer = (
                "I’m ready to chat, but Gemini is not configured.\n"
                "Check your GOOGLE_API_KEY in the .env file."
            )
        else:
            # ✅ NEW API: start_chat() with NO system_instruction argument
            if "chat" not in st.session_state:
                st.session_state.chat = GEM_MODEL.start_chat()

            chat_session = st.session_state.chat
            try:
                response = chat_session.send_message(prompt)
                answer = response.text
            except Exception as e:
                answer = (
                    "Oops, something went wrong while talking to the AI advisor. 😕\n"
                    f"Details: `{e}`"
                )

        # 3) Show + store assistant message
        with st.chat_message("assistant"):
            st.write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

    st.divider()
    st.markdown("### Example sample of master’s programs (synthetic data)")
    st.dataframe(
        df[["program", "university", "country", "field", "language", "ranking", "tuition_total"]],
        use_container_width=True,
    )
    st.markdown(
        "_Note: The table above is **synthetic example data** just to illustrate possible "
        "programs, fields, rankings and costs._"
    )

# ---------- TAB 2: Price Calculator ----------
with tab_price:
    st.subheader("Total Cost Calculator (Master’s)")
    with st.form("calc"):
        c1, c2 = st.columns(2)
        tuition = c1.number_input("Tuition total (€)", 0, 100000, 12000, 500)
        fees = c1.number_input("Other one-off fees (€)", 0, 5000, 500, 50)

        living = c2.number_input("Living cost per month (€)", 0, 5000, 900, 50)
        months = c2.number_input("Total months of study", 1, 60, 24, 1)

        c3, c4, c5 = st.columns(3)
        scholarship = c3.slider("Scholarship on tuition (%)", 0, 100, 20)
        exchange = c4.number_input(
            "Exchange rate (your currency per €)", 0.0, 10.0, 1.0, 0.01
        )
        part_time = c5.number_input(
            "Part-time income offset (€ / month)", 0, 5000, 0, 50
        )

        submitted = st.form_submit_button("Calculate")

    if submitted:
        tuition_net = tuition * (1 - scholarship / 100) + fees
        living_total = max(0, living - part_time) * months
        total_eur = round(tuition_net + living_total, 2)
        total_local = round(total_eur * exchange, 2)

        c1, c2 = st.columns(2)
        c1.metric("Total cost (€)", f"{total_eur:,.2f}")
        c2.metric("Total cost (local)", f"{total_local:,.2f}")
    # ---------- TAB 3: Map ----------
    with tab_map:
        st.subheader("Universities Map")
        render_university_map()

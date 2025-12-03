# app.py
# ===========================
# Masters Finder – Chatbot + Calculator
# ===========================
import base64
from pathlib import Path

import os
import streamlit as st

from calculator import render_price_calculator
from map_tab import render_university_map
from master_backend import ensure_embeddings, handle_user_query

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "..", "mm.png")
# ---------- Layout & session state ----------
st.set_page_config(page_title="MastersMatch", page_icon=LOGO_PATH, layout="wide")

def init_state():
    ss = st.session_state
    ss.setdefault("messages", [])  # [{"role": "user"/"assistant", "content": "..."}]

init_state()

# ---------- One-time backend init ----------
ensure_embeddings()

# ---------- Header with centered logo ----------

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

# ---------- Tabs ----------
tab_chat, tab_price, tab_map = st.tabs(
    [" Chat about Masters", "Price Calculator", "Map"]
)

# ---------- TAB 1: Chat about Masters ----------
with tab_chat:
    # show history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input(
        "Ask me about master's programs or specific details:"
    )

    if user_input:
    # user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

    # assistant reply using Mongo logic
        reply = handle_user_query(user_input)  # <- your friend's logic wrapped in a function

        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

# ---------- TAB 2: Price Calculator ----------
with tab_price:
    render_price_calculator()

# ---------- TAB 3: Map ----------
with tab_map:
    st.subheader("Universities Map")
    render_university_map()
